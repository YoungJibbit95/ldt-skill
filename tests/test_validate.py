"""Integrity regressions and local lifecycle integration for the read-only helper."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / ".agents/skills/architect-dev-team/scripts/validate.py"
spec = importlib.util.spec_from_file_location("validator", SCRIPT)
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / ".architect-dev-team").mkdir()
        (self.root / "app.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        self.architecture = self.root / ".architect-dev-team/architecture.md"
        self.architecture.write_text("# A1\nA small pure Python calculator.\n", encoding="utf-8")
        self.value = {
            "schema_version": 2, "phase": "INTAKE", "approval_stage": None,
            "profile": "lean", "architecture": None, "milestone": None,
            "approvals": [], "checks": [], "review": None,
            "completed": [], "open_issues": [], "constraints": [],
            "next_action": "Discover the calculator behavior",
        }

    def approve_architecture(self):
        self.value["architecture"] = {"path": ".architect-dev-team/architecture.md", "sha256": v.digest_file(self.architecture)}
        self.value["milestone"] = {"id": "M1", "summary": "Add two integers", "acceptance": ["2 + 3 equals 5"], "required_checks": ["acceptance"]}
        self.value["checks"] = [{"name": "acceptance", "required": True, "status": "not_run", "evidence": "", "waiver": None}]
        self.value["approvals"].append(self.decision("architecture"))

    def decision(self, kind, decision="approved"):
        return {"kind": kind, "decision": decision, "scope_sha256": v.scope(self.value),
                "review_sha256": self.value["review"]["sha256"] if kind == "iteration" else None,
                "evidence": "user message 42: approved M1", "recorded_at": "2026-10-18T17:00:00+02:00"}

    def ready_review(self):
        self.approve_architecture()
        self.value["checks"] = [{"name": "acceptance", "required": True, "status": "passed",
                                 "evidence": "python -m unittest: 1 passed", "waiver": None}]
        self.save_review()

    def save_review(self):
        path = self.root / ".architect-dev-team/review.json"
        path.write_bytes(v.canonical(v.snapshot(self.root)))
        self.value["review"] = {"path": ".architect-dev-team/review.json", "sha256": v.digest_file(path),
                                "independence": "self", "evidence": "reviewed calculator implementation and executed check"}

    def invalid(self, text, gate=None):
        with self.assertRaisesRegex(v.Invalid, text):
            v.state(self.value, self.root, gate)

    def test_initial_state_and_approval_stage(self):
        v.state(self.value, self.root)
        self.value["phase"] = "APPROVAL"
        self.invalid("approval_stage")
        self.value["approval_stage"] = "architecture"
        self.invalid("architecture approval stage requires architecture and milestone")
        self.approve_architecture()
        self.value["approvals"] = []
        v.state(self.value, self.root)

    def test_lifecycle_end_to_end_runs_real_code(self):
        # Real local execution, scope consent, manifest review, next-iteration gate.
        v.state(self.value, self.root)
        self.approve_architecture()
        self.value["phase"] = "IMPLEMENTATION"
        v.state(self.value, self.root)
        result = subprocess.run([sys.executable, "-c", "from app import add; assert add(2, 3) == 5"], cwd=self.root, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.value["checks"] = [{"name": "acceptance", "required": True, "status": "passed", "evidence": "executed 2+3 assertion, exit 0", "waiver": None}]
        self.save_review()
        self.value["phase"] = "PR_REVIEW"
        v.state(self.value, self.root)
        self.value["approvals"].append(self.decision("iteration"))
        self.value["phase"] = "NEXT_ITERATION"
        v.state(self.value, self.root)
        # Managed state writes and bytecode caches do not stale the approved source.
        (self.root / ".architect-dev-team/state.json").write_text("{}")
        v.state(self.value, self.root)

    def test_implement_requires_approval_for_every_profile(self):
        for profile in ("lean", "balanced", "rigorous"):
            self.value["profile"] = profile
            self.invalid("requires architecture", "implement")
        self.approve_architecture()
        self.value["approvals"] = []
        self.value["phase"] = "VERIFICATION"
        self.invalid("missing architecture approval")

    def test_rejection_supersedes_approval_even_with_older_timestamp(self):
        self.approve_architecture()
        reject = self.decision("architecture", "rejected")
        reject["recorded_at"] = "2025-01-01T00:00:00Z"
        self.value["approvals"].append(reject)
        self.invalid("rejected", "implement")

    def test_scope_change_and_architecture_bytes_invalidate(self):
        self.approve_architecture()
        self.value["milestone"]["summary"] = "Changed API"
        self.invalid("stale architecture", "implement")
        self.value["approvals"][-1]["scope_sha256"] = v.scope(self.value)
        self.architecture.write_text("changed")
        self.invalid("architecture artifact changed", "implement")

    def test_profile_change_invalidates_approved_scope(self):
        self.value["profile"] = "rigorous"
        self.approve_architecture()
        self.value["profile"] = "lean"
        self.invalid("stale architecture approval scope", "implement")

    def test_changed_missing_and_added_source_invalidate_review(self):
        self.ready_review()
        source = self.root / "app.py"
        for action in (lambda: source.write_text("changed"), lambda: source.unlink(), lambda: (self.root / "added.txt").write_text("new")):
            action()
            self.invalid("stale or incomplete", "review")
            self.save_review()

    def test_incomplete_manifest_rehashed_still_fails(self):
        self.ready_review()
        path = self.root / self.value["review"]["path"]
        manifest = v.snapshot(self.root)
        manifest["files"] = []
        path.write_bytes(v.canonical(manifest))
        self.value["review"]["sha256"] = v.digest_file(path)
        self.invalid("stale or incomplete", "review")

    def test_iteration_binds_review_bytes(self):
        self.ready_review()
        self.value["approvals"].append(self.decision("iteration"))
        v.state(self.value, self.root, "advance")
        path = self.root / self.value["review"]["path"]
        path.write_text(json.dumps(v.snapshot(self.root), indent=2))
        self.value["review"]["sha256"] = v.digest_file(path)
        self.invalid("stale iteration review", "advance")

    def test_review_requires_mandatory_checks_and_snapshot(self):
        self.approve_architecture()
        self.value["checks"] = []
        self.invalid("approved required_checks", "review")
        self.value["checks"] = [{"name": "acceptance", "required": True, "status": "passed", "evidence": "run passed", "waiver": None}]
        self.invalid("snapshot required", "review")

    def test_mandatory_failure_and_explicit_waivers(self):
        self.ready_review()
        check = self.value["checks"][0]
        for status in ("failed", "not_run", "unavailable"):
            check["status"] = status
            self.invalid("mandatory checks", "review")
        check["waiver"] = {"evidence": "user msg 99", "reason": "runner unavailable", "scope_sha256": v.scope(self.value)}
        self.invalid("only waived", "review")
        check["status"] = "waived"
        v.state(self.value, self.root, "review")
        check["waiver"] = None
        self.invalid("waiver", "review")

    def test_rigorous_independence_or_explicit_required_waiver(self):
        self.ready_review()
        self.value["profile"] = "rigorous"
        self.value["approvals"][-1]["scope_sha256"] = v.scope(self.value)
        for independence in ("unavailable", "self"):
            self.value["review"]["independence"] = independence
            self.invalid("rigorous review requires independent review", "review")
        self.value["review"]["independence"] = "independent"
        v.state(self.value, self.root, "review")
        self.value["review"]["independence"] = "unavailable"
        waiver = {"name": "independent_review", "required": False, "status": "waived",
                  "evidence": "user message 99", "waiver": {"evidence": "user message 99", "reason": "independent runtime unavailable", "scope_sha256": v.scope(self.value)}}
        self.value["checks"].append(waiver)
        self.invalid("rigorous review requires independent review", "review")
        waiver["required"] = True
        self.invalid("approved required_checks", "review")
        self.value["milestone"]["required_checks"].append("independent_review")
        self.value["approvals"][-1]["scope_sha256"] = v.scope(self.value)
        waiver["waiver"]["scope_sha256"] = v.scope(self.value)
        v.state(self.value, self.root, "review")
        waiver["name"] = "other_review"
        self.invalid("approved required_checks", "review")

    def test_approved_scope_repair_clears_stale_review(self):
        self.ready_review()
        approval_before = copy.deepcopy(self.value["approvals"])
        (self.root / "app.py").write_text("def add(a, b):\n    return int(a) + int(b)\n")
        self.value["phase"] = "IMPLEMENTATION"
        self.invalid("stale or incomplete", "implement")
        self.value["review"] = None
        self.value["checks"][0]["status"] = "not_run"
        self.value["checks"][0]["evidence"] = "Affected behavior changed; rerun required"
        v.state(self.value, self.root, "implement")
        self.assertEqual(self.value["approvals"], approval_before)
        self.invalid("mandatory checks block review", "review")

    def test_automatic_iteration_and_next_iteration_gates(self):
        self.ready_review()
        self.value["phase"] = "APPROVAL"
        self.value["approval_stage"] = "iteration"
        v.state(self.value, self.root)
        self.value["phase"] = "NEXT_ITERATION"
        self.value["approval_stage"] = None
        self.invalid("missing iteration")

    def test_malformed_shapes_types_and_unsafe_paths(self):
        original = copy.deepcopy(self.value)
        for field, malformed in (("schema_version", True), ("approvals", {}), ("profile", []), ("phase", []), ("checks", [None]), ("completed", "done")):
            self.value = copy.deepcopy(original)
            self.value[field] = malformed
            with self.subTest(field=field), self.assertRaises(v.Invalid):
                v.state(self.value, self.root)
        self.value = original
        for path in ("../x", "/x", "C:/x", "x\\y", "a/../x", "a//b"):
            self.value["architecture"] = {"path": path, "sha256": "0" * 64}
            self.invalid("unsafe relative path")

    def test_timestamp_requires_timezone_and_human_evidence(self):
        self.approve_architecture()
        item = self.value["approvals"][0]
        item["recorded_at"] = "2026-10-18T17:00:00"
        self.invalid("timezone")
        item["recorded_at"] = "2026-10-18T17:00:00Z"
        item["evidence"] = ""
        self.invalid("approval.evidence")

    def test_symlinks_rejected_when_platform_supports_them(self):
        target = self.root / "app.py"
        link = self.root / "linked.py"
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest("symlink creation unavailable")
        with self.assertRaisesRegex(v.Invalid, "symlink"):
            v.snapshot(self.root)

    @unittest.skipUnless(shutil.which("git"), "Git unavailable")
    def test_git_snapshot_head_ignores_and_deletions(self):
        def git(*args):
            result = subprocess.run(["git", "-c", "core.fsmonitor=false",
                                     "-c", f"core.hooksPath={self.root / 'no-hooks'}",
                                     "-c", "commit.gpgsign=false", "-C", str(self.root), *args], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result
        git("init", "-q")
        (self.root / ".gitignore").write_text("ignored.txt\n.architect-dev-team/\n")
        (self.root / "ignored.txt").write_text("not source")
        git("add", "app.py", ".gitignore")
        initial = v.snapshot(self.root)
        self.assertIsNone(initial["head_revision"])
        self.assertNotIn("ignored.txt", [item["path"] for item in initial["files"]])
        git("-c", "user.name=Evaluation", "-c", "user.email=eval@example.invalid", "commit", "-qm", "fixture")
        committed = v.snapshot(self.root)
        self.assertIsNotNone(committed["head_revision"])
        self.assertNotEqual(initial, committed)
        (self.root / "app.py").unlink()
        missing = next(item for item in v.snapshot(self.root)["files"] if item["path"] == "app.py")
        self.assertEqual((missing["type"], missing["sha256"], missing["executable_bits"]), ("missing", None, None))
        self.assertIsNotNone(missing["git_index"])
        self.assertNotIn("app.py", [item["path"] for item in v.snapshot(self.root, 1)["files"]])
        sub = self.root / "nested"
        sub.mkdir()
        with self.assertRaisesRegex(v.Invalid, "Git toplevel"):
            v.snapshot(sub)

    def test_cli_outputs_exit_status_and_no_writes(self):
        path = self.root / ".architect-dev-team/state.json"
        path.write_text(json.dumps(self.value))
        before = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        def cli(*args):
            return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)
        good = cli("state", path, "--root", self.root)
        self.assertEqual((good.returncode, good.stdout.strip()), (0, "OK state"))
        bad = cli("state", path, "--root", self.root, "--gate", "implement")
        self.assertEqual(bad.returncode, 1)
        self.assertNotIn("Traceback", bad.stderr)
        self.assertEqual(cli("scope", path).stdout.strip(), v.scope(self.value))
        self.assertEqual(cli("digest", path).stdout.strip(), v.digest_file(path))
        self.assertEqual(json.loads(cli("snapshot", self.root).stdout), v.snapshot(self.root))
        after = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        incomplete_scope = copy.deepcopy(self.value)
        del incomplete_scope["profile"]
        path.write_text(json.dumps(incomplete_scope))
        missing_profile = cli("scope", path)
        self.assertEqual(missing_profile.returncode, 1)
        self.assertIn("scope requires schema_version, architecture, milestone, and profile", missing_profile.stderr)

    def test_approved_check_policy_rejects_mutable_flag_bypasses(self):
        self.ready_review()
        baseline = copy.deepcopy(self.value)
        mutations = [lambda: self.value["checks"].clear(),
                     lambda: self.value["checks"][0].update(required=False),
                     lambda: self.value["checks"][0].update(name="renamed"),
                     lambda: self.value["checks"].append({"name": "new", "required": True, "status": "passed", "evidence": "run", "waiver": None})]
        for mutate in mutations:
            self.value = copy.deepcopy(baseline)
            mutate()
            for gate in ("implement", "review", "advance"):
                with self.subTest(gate=gate):
                    self.invalid("approved required_checks", gate)
        self.value = baseline
        self.value["checks"].append({"name": "optional", "required": False, "status": "failed", "evidence": "informational failure", "waiver": None})
        v.state(self.value, self.root, "review")

    def test_policy_changes_invalidate_scope_and_names_are_unique(self):
        self.approve_architecture()
        before = v.scope(self.value)
        self.value["milestone"]["required_checks"].append("lint")
        self.assertNotEqual(before, v.scope(self.value))
        self.invalid("stale architecture", "implement")
        self.value["milestone"]["required_checks"].append("lint")
        self.invalid("duplicate required check")

    def test_waiver_binds_profile_architecture_and_milestone_policy(self):
        self.ready_review()
        check = self.value["checks"][0]
        check.update(status="waived", waiver={"evidence": "human waiver 12", "reason": "runner unavailable", "scope_sha256": v.scope(self.value)})
        v.state(self.value, self.root, "review")
        for mutate in (lambda: self.value.update(profile="balanced"),
                       lambda: self.value["milestone"].update(summary="changed"),
                       lambda: self.value["milestone"]["required_checks"].append("lint")):
            previous = copy.deepcopy(self.value)
            mutate()
            self.invalid("stale waiver scope")
            self.value = previous
        self.value["checks"][0]["waiver"].pop("scope_sha256")
        self.invalid("waiver: expected fields")

    def legacy(self, reviewed=False):
        self.value["schema_version"] = 2
        self.ready_review() if reviewed else self.approve_architecture()
        self.value["schema_version"] = 1
        self.value["milestone"].pop("required_checks")
        self.value["approvals"][-1]["scope_sha256"] = v.scope(self.value)
        if reviewed:
            path = self.root / self.value["review"]["path"]
            path.write_bytes(v.canonical(v.snapshot(self.root, 1)))
            self.value["review"]["sha256"] = v.digest_file(path)

    def test_legacy_inspection_hash_and_all_gate_refusal(self):
        self.legacy(reviewed=True)
        expected = v.digest_bytes(v.canonical({key: self.value[key] for key in ("architecture", "milestone", "profile")}))
        self.assertEqual(v.scope(self.value), expected)
        v.state(self.value, self.root)
        for gate in ("implement", "review", "advance"):
            self.invalid("legacy schema v1.*migrate-state.*renewed architecture approval", gate)
        for phase in ("IMPLEMENTATION", "VERIFICATION", "PR_REVIEW", "NEXT_ITERATION"):
            self.value["phase"] = phase
            self.invalid("legacy schema v1")
        self.value.update(phase="APPROVAL", approval_stage="iteration")
        self.invalid("legacy schema v1")

    def test_migration_stale_review_policy_waiver_and_fresh_resume(self):
        self.legacy(reviewed=True)
        check = self.value["checks"][0]
        check.update(status="waived", waiver={"evidence": "legacy human waiver", "reason": "legacy runner absent"})
        approvals = copy.deepcopy(self.value["approvals"])
        self.value["phase"] = "NEXT_ITERATION"
        (self.root / "app.py").write_text("changed source")
        original = copy.deepcopy(self.value)
        with self.assertRaisesRegex(v.Invalid, "explicit --required-check"):
            v.migrate_state(self.value, self.root, [])
        migrated = v.migrate_state(self.value, self.root, ["acceptance", "lint"])
        self.assertEqual(self.value, original)
        self.value = migrated
        self.assertEqual(self.value["approvals"], approvals)
        self.assertEqual((self.value["phase"], self.value["approval_stage"]), ("APPROVAL", "architecture"))
        self.assertIsNone(self.value["review"])
        self.assertTrue(all(item["status"] == "not_run" and item["waiver"] is None for item in self.value["checks"]))
        self.assertIn("legacy human waiver", self.value["completed"][-1])
        self.assertLessEqual(len(self.value["completed"][-1]), 4096)
        self.invalid("stale architecture", "implement")
        self.value["approvals"].append(self.decision("architecture"))
        self.value.update(phase="IMPLEMENTATION", approval_stage=None)
        v.state(self.value, self.root)
        self.invalid("mandatory checks block review", "review")
        for item in self.value["checks"]:
            item.update(status="passed", evidence="fresh local run")
        self.save_review()
        v.state(self.value, self.root, "review")

    def test_migration_initial_and_artifact_failure(self):
        self.value["schema_version"] = 1
        result = v.migrate_state(self.value, self.root, [])
        self.assertEqual((result["schema_version"], result["phase"]), (2, "INTAKE"))
        with self.assertRaisesRegex(v.Invalid, "without a milestone omit"):
            v.migrate_state(self.value, self.root, ["unapproved"])
        self.legacy(reviewed=True)
        self.architecture.write_text("changed design")
        with self.assertRaisesRegex(v.Invalid, "architecture artifact changed"):
            v.migrate_state(self.value, self.root, ["acceptance"])

    def test_migration_cli_emits_only_json_and_never_writes(self):
        self.legacy(reviewed=True)
        path = self.root / ".architect-dev-team/state.json"
        path.write_bytes(v.canonical(self.value))
        before = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        command = [sys.executable, str(SCRIPT), "migrate-state", str(path), "--root", str(self.root), "--required-check", "explicit-policy", "--required-check", "another-check"]
        result = subprocess.run(command, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        emitted = json.loads(result.stdout.decode("utf-8"))
        self.assertEqual(emitted["milestone"]["required_checks"], ["explicit-policy", "another-check"])
        self.assertFalse(next(item for item in emitted["checks"] if item["name"] == "acceptance")["required"])
        self.assertEqual(result.stderr, b"")
        after = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_migration_summary_bounded_and_invalid_input_refused(self):
        self.legacy(reviewed=True)
        self.value["checks"][0]["evidence"] = "historical check evidence " * 500
        migrated = v.migrate_state(self.value, self.root, ["acceptance"])
        self.assertLessEqual(len(migrated["completed"][-1]), 4096)
        self.assertIn("summary truncated", migrated["completed"][-1])
        self.assertIn("legacy_state_sha256", migrated["completed"][-1])
        with self.assertRaisesRegex(v.Invalid, "duplicate required check"):
            v.migrate_state(self.value, self.root, ["acceptance", "acceptance"])
        with self.assertRaisesRegex(v.Invalid, "requires legacy schema v1"):
            v.migrate_state(migrated, self.root, ["acceptance"])

    def test_migration_refuses_changed_or_malformed_review_artifact(self):
        self.legacy(reviewed=True)
        path = self.root / self.value["review"]["path"]
        path.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(v.Invalid, "review artifact changed"):
            v.migrate_state(self.value, self.root, ["acceptance"])
        self.value["review"]["sha256"] = v.digest_file(path)
        with self.assertRaisesRegex(v.Invalid, "legacy review snapshot: expected fields"):
            v.migrate_state(self.value, self.root, ["acceptance"])

    def test_scope_validates_schema_specific_fields(self):
        self.approve_architecture()
        original = copy.deepcopy(self.value)
        for milestone in ({"id": "M1", "summary": "summary", "acceptance": ["ok"]},
                          {"id": "M1", "summary": "summary", "acceptance": ["ok"], "required_checks": []},
                          {"id": "M1", "summary": "summary", "acceptance": [], "required_checks": []},
                          {"id": "M1", "summary": "summary", "acceptance": ["ok"], "required_checks": ["x", "x"]}):
            self.value = copy.deepcopy(original)
            self.value["milestone"] = milestone
            with self.assertRaises(v.Invalid):
                v.scope(self.value)

    def test_schema1_review_is_not_schema2_coverage(self):
        self.ready_review()
        path = self.root / self.value["review"]["path"]
        path.write_bytes(v.canonical(v.snapshot(self.root, 1)))
        self.value["review"]["sha256"] = v.digest_file(path)
        self.invalid("current schema coverage required", "review")

    def test_mode_snapshot_drift_and_posix_exact_mask(self):
        self.ready_review()
        path = self.root / "app.py"
        for mode, expected in ((0o100751, 0o111), (0o100650, 0o010), (0o100701, 0o101)):
            metadata = type("Metadata", (), {"st_mode": mode})()
            with mock.patch.object(type(path), "stat", return_value=metadata), mock.patch.object(v.os, "name", "posix"):
                self.assertEqual(v.file_metadata(path), {"type": "regular", "executable_bits": expected})
        with mock.patch.dict(v.snapshot.__globals__, file_metadata=mock.Mock(return_value={"type": "regular", "executable_bits": 0o010})):
            self.invalid("stale or incomplete", "review")
        if os.name == "nt":
            self.assertTrue(all(item["executable_bits"] is None for item in v.snapshot(self.root)["files"]))

    @unittest.skipUnless(os.name == "posix", "POSIX executable bits unavailable on this OS")
    def test_real_posix_executable_change(self):
        source = self.root / "app.py"
        source.chmod(0o640)
        self.ready_review()
        source.chmod(0o650)
        self.invalid("stale or incomplete", "review")

    def test_walk_permission_failure_is_not_silently_omitted(self):
        denied = self.root / "denied"
        denied.mkdir()
        real_scandir = os.scandir
        def scandir(path):
            if Path(path) == denied:
                raise PermissionError(13, "Permission denied", str(path))
            return real_scandir(path)
        # Keep the real os.walk implementation; mock the actual failing syscall.
        with mock.patch.object(v.os, "scandir", side_effect=scandir):
            with self.assertRaisesRegex(v.Invalid, "snapshot traversal failed.*denied.*restore access"):
                v.snapshot(self.root)

    @unittest.skipUnless(shutil.which("git"), "Git unavailable")
    def test_git_success_with_enumeration_diagnostics_fails_closed(self):
        self.fixture_git("init", "-q")
        self.fixture_git("add", "app.py")
        actual_git = v.git
        for stage_inventory in (False, True):
            def reported(root, *args):
                result = actual_git(root, *args)
                if args and args[0] == "ls-files" and (("--stage" in args) == stage_inventory):
                    self.assertEqual(result.returncode, 0)
                    result.stderr = b"warning: could not open directory blocked/: Permission denied\n"
                return result
            with self.subTest(stage_inventory=stage_inventory), mock.patch.dict(v.snapshot.__globals__, git=mock.Mock(side_effect=reported)):
                with self.assertRaisesRegex(v.Invalid, "reported diagnostics"):
                    v.snapshot(self.root)

    def test_nul_path_rejected_safely_by_cli(self):
        with self.assertRaisesRegex(v.Invalid, "unsupported NUL.*\\\\x00"):
            v.relative("bad\x00.md")
        self.value["architecture"] = {"path": "bad\x00.md", "sha256": "0" * 64}
        path = self.root / ".architect-dev-team/state.json"
        path.write_text(json.dumps(self.value), encoding="utf-8")
        result = subprocess.run([sys.executable, str(SCRIPT), "state", str(path), "--root", str(self.root)], capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn(b"unsupported NUL", result.stderr)
        self.assertIn(b"\\x00", result.stderr)
        self.assertNotIn(b"Traceback", result.stderr)

    def test_non_utf8_paths_have_lossless_ascii_diagnostic(self):
        bad = "bad-\udcff.py"
        for operation in (lambda: v.relative(bad),
                          lambda: v.snapshot(self.root)):
            with mock.patch.object(v.os, "walk", return_value=iter([(str(self.root), [], [bad])])):
                with self.assertRaises(v.Invalid) as caught:
                    operation()
            message = str(caught.exception)
            self.assertIn("non-UTF8 path", message)
            self.assertIn("\\udcff", message)
            self.assertTrue(message.isascii())

    @unittest.skipUnless(os.name == "posix", "raw non-UTF8 filesystem names unavailable on this OS")
    def test_real_non_utf8_filename(self):
        raw_path = os.fsencode(self.root) + b"/bad-\xff.py"
        descriptor = os.open(raw_path, os.O_CREAT | os.O_WRONLY, 0o600)
        os.close(descriptor)
        with self.assertRaisesRegex(v.Invalid, "non-UTF8 path.*\\\\udcff"):
            v.snapshot(self.root)
        if shutil.which("git"):
            self.fixture_git("init", "-q")
            self.fixture_git("add", "--all")
            with self.assertRaisesRegex(v.Invalid, "non-UTF8 path.*\\\\udcff"):
                v.snapshot(self.root)

    def fixture_git(self, *args, cwd=None, input=None):
        project = cwd or self.root
        result = subprocess.run(["git", "-c", "core.fsmonitor=false", "-c", f"core.hooksPath={self.root / 'no-hooks'}",
                                 "-c", "commit.gpgsign=false", "-C", str(project), *args], input=input, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    @unittest.skipUnless(shutil.which("git"), "Git unavailable")
    def test_git_staged_mode_and_blob_changes_invalidate_review(self):
        self.fixture_git("init", "-q")
        self.fixture_git("add", "app.py")
        self.ready_review()
        original = v.snapshot(self.root)
        entry = next(item for item in original["files"] if item["path"] == "app.py")
        self.assertEqual(entry["git_index"]["stage"], 0)
        self.fixture_git("update-index", "--chmod=+x", "app.py")
        self.invalid("stale or incomplete", "review")
        self.save_review()
        source = self.root / "app.py"
        original_bytes = source.read_bytes()
        source.write_text("staged content")
        self.fixture_git("add", "app.py")
        source.write_bytes(original_bytes)
        self.invalid("stale or incomplete", "review")

    @unittest.skipUnless(shutil.which("git"), "Git unavailable")
    def test_missing_tracked_file_staged_mode_and_blob_still_bound(self):
        self.fixture_git("init", "-q")
        self.fixture_git("add", "app.py")
        old_blob = self.fixture_git("rev-parse", ":app.py").stdout.strip().decode("ascii")
        (self.root / "app.py").unlink()
        self.ready_review()
        self.fixture_git("update-index", "--cacheinfo", "100755", old_blob, "app.py")
        self.invalid("stale or incomplete", "review")
        self.save_review()
        blob = self.fixture_git("hash-object", "-w", "--stdin", input=b"new staged content").stdout.strip().decode("ascii")
        self.fixture_git("update-index", "--cacheinfo", "100755", blob, "app.py")
        self.invalid("stale or incomplete", "review")

    def test_migration_refuses_output_over_state_limit(self):
        self.legacy()
        # Keep original valid input under64KiB, but leave insufficient room for
        # the bounded migration audit. Never emit an unusable proposal.
        self.value["completed"] = ["x" * (64 * 1024 - len(v.canonical(self.value)) - 100)]
        self.assertLess(len(v.canonical(self.value)), 64 * 1024)
        with self.assertRaisesRegex(v.Invalid, "migrated state exceeds.*compact the original"):
            v.migrate_state(self.value, self.root, ["acceptance"])

    @unittest.skipUnless(shutil.which("git"), "Git unavailable")
    def test_git_unmerged_index_is_explicitly_rejected(self):
        self.fixture_git("init", "-q")
        self.fixture_git("add", "app.py")
        blob = self.fixture_git("rev-parse", ":app.py").stdout.strip()
        self.fixture_git("update-index", "--force-remove", "app.py")
        self.fixture_git("update-index", "--index-info", input=b"100644 " + blob + b" 1\tapp.py\n100644 " + blob + b" 2\tapp.py\n")
        with self.assertRaisesRegex(v.Invalid, "app.py: unmerged Git index stage.*manual resolution"):
            v.snapshot(self.root)

    @unittest.skipUnless(shutil.which("git"), "Git unavailable")
    def test_initialized_and_uninitialized_gitlinks_fail_closed(self):
        source_temp = tempfile.TemporaryDirectory()
        self.addCleanup(source_temp.cleanup)
        source = Path(source_temp.name)
        self.fixture_git("init", "-q", cwd=source)
        (source / "module.py").write_text("local submodule")
        self.fixture_git("add", "module.py", cwd=source)
        self.fixture_git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture", cwd=source)
        self.fixture_git("init", "-q")
        self.fixture_git("-c", "protocol.file.allow=always", "submodule", "add", "--quiet", str(source), "local-module")
        for initialized in (True, False):
            if not initialized:
                self.fixture_git("submodule", "deinit", "-f", "--", "local-module")
            with self.subTest(initialized=initialized), self.assertRaisesRegex(v.Invalid, "local-module: unsupported submodule/gitlink; manual verification required; automated review/advance unavailable"):
                v.snapshot(self.root)

    @unittest.skipUnless(shutil.which("git"), "Git unavailable")
    def test_broken_head_is_not_treated_as_unborn(self):
        self.fixture_git("init", "-q")
        self.fixture_git("add", "app.py")
        self.fixture_git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture")
        head = self.root / ".git/HEAD"
        head.write_text("a" * 40 + "\n", encoding="ascii")
        with self.assertRaisesRegex(v.Invalid, "Git HEAD inspection failed"):
            v.snapshot(self.root)

    def test_json_size_limit_duplicate_keys_and_invalid_input(self):
        path = self.root / "invalid.json"
        for data in (b'{"a":1,"a":2}', b'{"x": NaN}', b'\xff', b'{'):
            path.write_bytes(data)
            with self.assertRaises(v.Invalid):
                v.read_json(path, 1024)
        path.write_bytes(b" " * (64 * 1024 + 1))
        with self.assertRaisesRegex(v.Invalid, "exceeds"):
            v.read_json(path, 64 * 1024)

    def test_cli_unicode_output_and_errors_under_legacy_encoding(self):
        (self.root / "名.py").write_text("value = 1\n", encoding="utf-8")
        env = dict(os.environ, PYTHONIOENCODING="cp1252")
        result = subprocess.run([sys.executable, str(SCRIPT), "snapshot", str(self.root)],
                                env=env, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8"))
        manifest = json.loads(result.stdout.decode("utf-8"))
        self.assertIn("名.py", [item["path"] for item in manifest["files"]])
        self.value["architecture"] = {"path": "../名.py", "sha256": "0" * 64}
        path = self.root / ".architect-dev-team/state.json"
        path.write_text(json.dumps(self.value, ensure_ascii=False), encoding="utf-8")
        invalid = subprocess.run([sys.executable, str(SCRIPT), "state", str(path), "--root", str(self.root)],
                                 env=env, capture_output=True)
        self.assertEqual(invalid.returncode, 1)
        diagnostic = invalid.stderr.decode("utf-8")
        self.assertIn("unsafe relative path: ../名.py", diagnostic)
        self.assertNotIn("Traceback", diagnostic)


class Registry(unittest.TestCase):
    def setUp(self):
        self.entry = {"id": "sample", "name": "Sample", "description": "A fixture", "author": "Example", "maintainer": "Team",
                      "repository": "https://github.com/example/skills", "path": "skills/sample", "revision": "a" * 40,
                      "license": {"spdx": "MIT", "url": "https://github.com/example/skills/blob/" + "a" * 40 + "/LICENSE", "attribution": "Example"},
                      "use_cases": ["fixture"], "compatibility": ["Codex"], "trust": "candidate", "last_review_date": "2026-10-18", "limitations": [],
                      "installation": {"instructions": "Request consent then use pinned source"},
                      "evidence": [{"kind": "provenance", "reference": "https://github.com/example/skills", "summary": "fixture source", "date": "2026-10-18"}]}

    def validate(self):
        v.registry({"schema_version": 1, "skills": [self.entry]})

    def test_candidate_provenance_and_duplicate_ids(self):
        self.validate()
        with self.assertRaisesRegex(v.Invalid, "duplicate registry"):
            v.registry({"schema_version": 1, "skills": [self.entry, self.entry]})
        self.entry["evidence"] = []
        with self.assertRaisesRegex(v.Invalid, "provenance"):
            self.validate()

    def test_trust_requires_cumulative_evidence(self):
        for trust, needed in (("reviewed", ["review"]), ("tested", ["review", "test"]), ("approved", ["review", "test", "approval"])):
            self.entry["trust"] = trust
            self.entry["evidence"] = self.entry["evidence"][:1]
            with self.assertRaises(v.Invalid):
                self.validate()
            for kind in needed:
                self.entry["evidence"].append({"kind": kind, "reference": "fixture evidence", "summary": "bounded review", "date": "2026-10-18"})
            self.validate()

    def test_invalid_registry_fields(self):
        baseline = copy.deepcopy(self.entry)
        for key, value in (("revision", "main"), ("repository", "http://example.com/repo"), ("path", "../outside"), ("last_review_date", "2026-02-30"), ("trust", []), ("evidence", [None])):
            self.entry = copy.deepcopy(baseline)
            self.entry[key] = value
            with self.subTest(key=key), self.assertRaises(v.Invalid):
                self.validate()


class Package(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        files = ["SKILL.md", "agents/openai.yaml", "registry/skills.json", "assets/state.template.json",
                 "assets/architecture.template.md", "scripts/validate.py"]
        files += [f"scripts/ldt_core/{name}.py" for name in
                  ("__init__", "common", "snapshots", "approvals", "state", "registry", "package")]
        files += [f"references/{name}.md" for name in ("architecture", "delegation", "approvals", "delivery", "external-skills", "project-memory", "evaluation")]
        for value in files:
            path = self.root / value
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture", encoding="utf-8")
        (self.root / "SKILL.md").write_text("---\nname: architect-dev-team\ndescription: Architecture-first development\n---\n[Guide](references/architecture.md)\n", encoding="utf-8")
        (self.root / "registry/skills.json").write_text('{"schema_version":1,"skills":[]}', encoding="utf-8")

    def test_package_links_and_required_files(self):
        v.package(self.root)
        (self.root / "references/architecture.md").write_text("[State](../assets/state.template.json)")
        v.package(self.root)
        (self.root / "SKILL.md").write_text("---\nname: architect-dev-team\ndescription: Development\n---\n[Outside](../outside.md)\n")
        with self.assertRaisesRegex(v.Invalid, "escapes package"):
            v.package(self.root)
        (self.root / "agents/openai.yaml").unlink()
        with self.assertRaisesRegex(v.Invalid, "missing file"):
            v.package(self.root)

    def test_package_unfinished_frontmatter(self):
        (self.root / "SKILL.md").write_text("---\nname: architect-dev-team\ndescription: TODO\n---\n")
        with self.assertRaisesRegex(v.Invalid, "unfinished"):
            v.package(self.root)


if __name__ == "__main__":
    unittest.main()
