"""Read-only registry compatibility, migration and hostile-input checks."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[1]
PACKAGE = REPO / ".agents/skills/architect-dev-team"
SCRIPT = PACKAGE / "scripts/validate.py"
BASELINE = REPO / "tests/fixtures/m1a-baseline/validate.py"
LEGACY = PACKAGE / "registry/skills.json"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RegistryV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = load(BASELINE, "registry_baseline")
        cls.new = load(SCRIPT, "registry_facade")
        cls.original_bytes = LEGACY.read_bytes()
        cls.legacy = json.loads(cls.original_bytes)

    def setUp(self):
        temporary_root = Path(os.environ.get("TEMP", tempfile.gettempdir()))
        temporary_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temporary_root)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = dict(os.environ, TEMP=str(temporary_root), TMP=str(temporary_root),
                        PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")

    def record(self, identity="example"):
        entry = copy.deepcopy(self.legacy["skills"][0])
        entry.update(id=identity, name=identity, repository="https://github.com/example/skills",
                     path="skills/" + identity, revision="a" * 40, trust="candidate")
        prefix = entry["repository"] + "/blob/" + entry["revision"] + "/"
        entry["license"]["url"] = prefix + "LICENSE"
        entry["evidence"] = [{"kind": "provenance", "reference": prefix + entry["path"] + "/SKILL.md",
                              "summary": "Pinned manifest inspection only", "date": "2026-10-18"}]
        return {"schema_version": 2, "metadata": entry, "aliases": [],
                "verification": {"status": "source-verified", "manifest_url": prefix + entry["path"] + "/SKILL.md",
                                 "manifest_sha256": "b" * 64, "license_status": "verified",
                                 "license_sha256": "c" * 64, "checked_at": "2026-10-18",
                                 "alias_evidence": [], "unknowns": []},
                "runtime": {"requirements": ["Python"], "effects": ["May invoke CLI"],
                            "unknowns": ["No executable review performed"]},
                "lifecycle": {"status": "unknown", "reference": None, "reason": "Not established"}}

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def index(self, records):
        index = {"schema_version": 2, "records": []}
        for record in records:
            identity = record["metadata"]["id"]
            relative = "skills/" + identity + ".json"
            self.write(self.root / relative, record)
            index["records"].append({"id": identity, "path": relative})
        return index

    def cli(self, args, script=SCRIPT):
        return subprocess.run([sys.executable, "-B", str(script), *map(str, args)],
                              cwd=self.root, env=self.env, capture_output=True)

    def snapshot(self, root):
        return {str(path.relative_to(root)): (path.read_bytes(), path.stat().st_mtime_ns)
                for path in root.rglob("*") if path.is_file()}

    def assert_invalid_cli(self, path, *extra):
        result = self.cli(["registry", path, *extra])
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, b"")
        self.assertIn(b"INVALID:", result.stderr)
        self.assertNotIn(b"Traceback", result.stderr)

    def test_schema1_differential_core_and_cli(self):
        variants = [copy.deepcopy(self.legacy), {"schema_version": 1, "skills": []}]
        for edit in (lambda v: v.update(schema_version=True),
                     lambda v: v["skills"].append(copy.deepcopy(v["skills"][0])),
                     lambda v: v["skills"][0].update(revision="main"),
                     lambda v: v["skills"][0].update(trust="approved"),
                     lambda v: v["skills"][0]["license"].update(url="http://example.com/LICENSE"),
                     lambda v: v["skills"][0].update(unexpected=True)):
            value = copy.deepcopy(self.legacy)
            edit(value)
            variants.append(value)
        def outcome(module, value):
            try:
                return ("return", module.registry(copy.deepcopy(value)))
            except Exception as exc:
                return (type(exc).__name__, str(exc))
        for number, value in enumerate(variants):
            with self.subTest(case=number):
                self.assertEqual(outcome(self.old, value), outcome(self.new, value))
                path = self.write(self.root / "legacy.json", value)
                old, new = self.cli(["registry", path], BASELINE), self.cli(["registry", path])
                self.assertEqual((old.returncode, old.stdout, old.stderr),
                                 (new.returncode, new.stdout, new.stderr))

    def test_valid_record_index_and_empty_index(self):
        record = self.record()
        original = copy.deepcopy(record)
        self.assertIsNone(self.new.registry_record(record))
        index = self.index([record])
        self.assertIsNone(self.new.registry(index, self.root))
        self.assertIsNone(self.new.registry({"schema_version": 2, "records": []}, self.root))
        self.assertEqual(record, original)
        with self.assertRaises(self.new.Invalid):
            self.new.registry(index)

    def test_record_malformed_and_unpinned_assertions_fail_cleanly(self):
        edits = {
            "schema bool": lambda r: r.update(schema_version=True),
            "unsupported schema": lambda r: r.update(schema_version=3),
            "extra wrapper field": lambda r: r.update(unexpected=True),
            "missing runtime": lambda r: r.pop("runtime"),
            "null metadata": lambda r: r.update(metadata=None),
            "mutable revision": lambda r: r["metadata"].update(revision="main"),
            "uppercase revision": lambda r: r["metadata"].update(revision="A" * 40),
            "short hash": lambda r: r["verification"].update(manifest_sha256="b" * 63),
            "uppercase hash": lambda r: r["verification"].update(license_sha256="C" * 64),
            "hash type": lambda r: r["verification"].update(manifest_sha256=[]),
            "wrong manifest revision": lambda r: r["verification"].update(manifest_url=r["verification"]["manifest_url"].replace("a" * 40, "d" * 40)),
            "foreign license": lambda r: r["metadata"]["license"].update(url="https://github.com/foreign/repo/blob/" + "a" * 40 + "/LICENSE"),
            "mutable license": lambda r: r["metadata"]["license"].update(url="https://github.com/example/skills/blob/main/LICENSE"),
            "encoded path": lambda r: r["metadata"].update(path="skills/%2e%2e/escape"),
            "query source path": lambda r: (r["metadata"].update(path="skills/example?raw=1"), r["verification"].update(manifest_url="https://github.com/example/skills/blob/" + "a" * 40 + "/skills/example?raw=1/SKILL.md")),
            "IPv6 malformed repository": lambda r: r["metadata"].update(repository="https://[invalid"),
            "manifest as directory": lambda r: r["metadata"].update(path="skills/example/SKILL.md"),
            "bad date": lambda r: r["verification"].update(checked_at="2026-02-30"),
            "unsupported verification": lambda r: r["verification"].update(status="approved"),
            "unknown verified license": lambda r: r["metadata"]["license"].update(spdx="UNKNOWN"),
            "nonlicense text": lambda r: r["metadata"]["license"].update(url=r["verification"]["manifest_url"]),
            "malformed alias": lambda r: r.update(aliases=["../bad"]),
            "alias without proof": lambda r: r.update(aliases=["another"]),
            "no provenance": lambda r: r["metadata"].update(evidence=[]),
            "foreign provenance": lambda r: r["metadata"]["evidence"][0].update(reference="https://github.com/foreign/repo/blob/" + "a" * 40 + "/SKILL.md"),
            "strong trust unresolved": lambda r: r["metadata"].update(trust="approved"),
        }
        for label, edit in edits.items():
            with self.subTest(case=label):
                value = self.record()
                edit(value)
                with self.assertRaises(self.new.Invalid):
                    self.new.registry_record(value)
                self.assert_invalid_cli(self.write(self.root / "record.json", value))

    def test_unknown_or_declared_license_is_explicit(self):
        record = self.record()
        record["verification"].update(license_status="declared", license_sha256=None,
                                      unknowns=["Manifest declaration; applicable text unverified"])
        record["metadata"]["license"]["url"] = record["verification"]["manifest_url"]
        self.new.registry_record(record)
        record["verification"]["unknowns"] = []
        with self.assertRaises(self.new.Invalid):
            self.new.registry_record(record)

    def test_stronger_trust_needs_current_source_bound_evidence(self):
        record = self.record()
        record["metadata"]["trust"] = "approved"
        record["runtime"]["unknowns"] = []
        for kind in ("review", "test", "approval"):
            record["metadata"]["evidence"].append({"kind": kind,
                "reference": record["verification"]["manifest_url"],
                "summary": "Synthetic current-source evidence", "date": "2026-10-18"})
        self.new.registry_record(record)
        for reference in ("https://github.com/foreign/repo/blob/" + "a" * 40 + "/SKILL.md",
                          "https://example.com/unrelated/" + "a" * 40,
                          "legacy prose mentioning " + "a" * 40):
            value = copy.deepcopy(record)
            value["metadata"]["evidence"][-1]["reference"] = reference
            with self.subTest(reference=reference), self.assertRaises(self.new.Invalid):
                self.new.registry_record(value)

    def test_raw_url_controls_cannot_be_normalized_into_verified_sources(self):
        for control in ("\r", "\n", "\t"):
            for field in ("source", "license", "provenance", "lifecycle"):
                record = self.record()
                if field == "source":
                    record["metadata"]["path"] = "skills/exam" + control + "ple"
                    record["verification"]["manifest_url"] = (
                        record["metadata"]["repository"] + "/blob/" +
                        record["metadata"]["revision"] + "/" + record["metadata"]["path"] + "/SKILL.md")
                elif field == "license":
                    record["metadata"]["license"]["url"] += control
                elif field == "provenance":
                    record["metadata"]["evidence"][0]["reference"] += control
                else:
                    record["lifecycle"].update(status="observed",
                        reference=record["verification"]["manifest_url"] + control)
                with self.subTest(control=repr(control), field=field):
                    with self.assertRaises(self.new.Invalid):
                        self.new.registry_record(record)
                    self.assert_invalid_cli(self.write(self.root / "control.json", record))

    def test_surrogate_assertions_fail_schema2_cleanly(self):
        for section, field in (("metadata", "description"), ("runtime", "unknowns")):
            record = self.record()
            record[section][field] = "unpaired \ud800" if section == "metadata" else ["unpaired \udfff"]
            with self.subTest(section=section):
                with self.assertRaises(self.new.Invalid):
                    self.new.registry_record(record)
                path = self.write(self.root / "surrogate.json", record)
                self.assert_invalid_cli(path)
                index = self.index([record])
                with self.assertRaises(self.new.Invalid):
                    self.new.registry(index, self.root)
                self.assert_invalid_cli(self.write(self.root / "index.json", index))

    def test_surrogate_legacy_migration_preserves_values_in_explicit_draft(self):
        value = copy.deepcopy(self.legacy)
        value["skills"][0]["description"] = "Legacy lone high \ud800 and low \udfff assertions"
        value["skills"][0]["limitations"].append("Unknown \ud800 assertion")
        before = copy.deepcopy(value)
        self.old.registry(value)
        proposal = self.new.migrate_registry(value)
        self.assertEqual(value, before)
        self.assertEqual(proposal["source"], before)
        self.assertEqual(proposal["records"][0]["value"]["metadata"], before["skills"][0])
        self.assertEqual(proposal["source_encoding"], "canonical-json-ascii")
        encoded = json.dumps(before, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        self.assertEqual(proposal["source_sha256"], hashlib.sha256(encoded).hexdigest())
        self.assertFalse(proposal["ready_for_validation"])
        self.assertTrue(proposal["validation_issues"])
        path = self.write(self.root / "legacy-surrogate.json", value)
        files_before = self.snapshot(self.root)
        result = self.cli(["registry", path, "--migration-proposal"])
        self.assertEqual((result.returncode, result.stderr), (0, b""))
        result.stdout.decode("ascii")
        self.assertEqual(json.loads(result.stdout), proposal)
        self.assertEqual(files_before, self.snapshot(self.root))
        self.assertEqual(value, before)

    def test_alias_proof_and_global_identity_collisions(self):
        first = self.record("first")
        first["aliases"] = ["first-alias"]
        first["verification"]["alias_evidence"] = [{"alias": "first-alias",
            "reference": first["verification"]["manifest_url"], "summary": "Pinned name assertion"}]
        self.new.registry_record(first)
        for label, edit in {
            "name": lambda r: r["metadata"].update(name="first"),
            "alias": lambda r: r["metadata"].update(name="first-alias"),
            "upstream": lambda r: r["metadata"].update(path="skills/first"),
        }.items():
            second = self.record("second")
            edit(second)
            second["verification"]["manifest_url"] = second["metadata"]["repository"] + "/blob/" + second["metadata"]["revision"] + "/" + second["metadata"]["path"] + "/SKILL.md"
            with self.subTest(case=label), self.assertRaises(self.new.Invalid):
                self.new.registry(self.index([first, second]), self.root)
        for change in (lambda r: r["aliases"].append("first-alias"),
                       lambda r: r["verification"]["alias_evidence"][0].update(reference="https://github.com/elsewhere/repo/blob/" + "a" * 40 + "/README.md")):
            value = copy.deepcopy(first)
            change(value)
            with self.assertRaises(self.new.Invalid):
                self.new.registry_record(value)

    def test_index_paths_ids_and_versions_fail_closed(self):
        good = self.index([self.record()])
        for path in ("../outside.json", "/absolute.json", "skills/../../escape.json",
                     "skills\\example.json", "skills/example.json:stream", "skills/%2e%2e.json",
                     "skills/example.json\x00"):
            value = copy.deepcopy(good)
            value["records"][0]["path"] = path
            with self.subTest(path=path), self.assertRaises(self.new.Invalid):
                self.new.registry(value, self.root)
        for value in ({"schema_version": 3, "records": []}, {"schema_version": True, "records": []},
                      {"schema_version": 2, "records": None},
                      {"schema_version": 2, "records": good["records"] * 2},
                      {"schema_version": 2, "records": [{"id": "other", "path": "skills/other.json"}]},
                      {"schema_version": 2, "records": [], "extra": True}):
            with self.subTest(value=value), self.assertRaises(self.new.Invalid):
                self.new.registry(value, self.root)

    def test_wrong_json_types_are_invalid_not_python_exceptions(self):
        fields = [("metadata", "revision"), ("metadata", "trust"),
                  ("verification", "status"), ("verification", "license_status"),
                  ("verification", "manifest_url"), ("verification", "checked_at"),
                  ("lifecycle", "status"), ("lifecycle", "reference"),
                  ("runtime", "requirements")]
        for section, field in fields:
            for wrong in (None, False, 42, [], {}):
                value = self.record()
                value[section][field] = wrong
                if section == "lifecycle" and field == "reference" and wrong is None:
                    continue  # Unknown lifecycle explicitly requires null.
                if section == "runtime" and wrong == []:
                    continue  # Runtime uncertainty can cover unknown requirements.
                with self.subTest(section=section, field=field, wrong=wrong):
                    with self.assertRaises(self.new.Invalid):
                        self.new.registry_record(value)

    def test_migration_invalid_legacy_ids_remain_unmodified_drafts(self):
        value = copy.deepcopy(self.legacy)
        value["skills"][0]["id"] = "../unsafe-original-id"
        before = copy.deepcopy(value)
        proposal = self.new.migrate_registry(value)
        self.assertEqual(value, before)
        self.assertEqual(proposal["source"], before)
        self.assertEqual(proposal["records"][0]["value"]["metadata"], before["skills"][0])
        self.assertIsNone(proposal["records"][0]["path"])
        self.assertFalse(proposal["ready_for_validation"])
        self.assertTrue(proposal["validation_issues"])

    def test_missing_files_and_malformed_records_are_clean(self):
        for path in (self.root / "absent.json", self.root / "absent-parent/index.json"):
            with self.subTest(path=path):
                with self.assertRaises((self.new.Invalid, OSError)):
                    self.new.registry_file(path)
                self.assert_invalid_cli(path)
        index = {"schema_version": 2, "records": [{"id": "example", "path": "skills/example.json"}]}
        index_path = self.write(self.root / "index.json", index)
        self.assert_invalid_cli(index_path)
        record_path = self.root / "skills/example.json"
        record_path.parent.mkdir(exist_ok=True)
        for raw in (b"{", b'{"schema_version":2,"schema_version":2}', b"null", b"[]", b"\xff", b'{"x":NaN}'):
            record_path.write_bytes(raw)
            with self.subTest(raw=raw):
                with self.assertRaises(self.new.Invalid):
                    self.new.registry_file(index_path)
                self.assert_invalid_cli(index_path)

    def test_registry_size_limits_fail_closed(self):
        index = {"schema_version": 2, "records": [{"id": "example", "path": "skills/example.json"}] * 257}
        with self.assertRaisesRegex(self.new.Invalid, "256"):
            self.new.registry(index, self.root)
        path = self.root / "oversize.json"
        path.write_bytes(b" " * (1024 * 1024 + 1))
        with self.assertRaises(self.new.Invalid):
            self.new.registry_file(path)
        self.assert_invalid_cli(path)

    def test_symlink_file_and_directory_are_rejected(self):
        outside = self.write(self.root / "outside.json", self.record())
        registry_root = self.root / "registry"
        (registry_root / "skills").mkdir(parents=True)
        path = registry_root / "skills/example.json"
        try:
            path.symlink_to(outside)
        except OSError as exc:
            self.skipTest("Host cannot create symlinks: " + str(exc))
        index = {"schema_version": 2, "records": [{"id": "example", "path": "skills/example.json"}]}
        with self.assertRaises(self.new.Invalid):
            self.new.registry(index, registry_root)
        path.unlink()
        path.parent.rmdir()
        path.parent.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(self.new.Invalid):
            self.new.registry(index, registry_root)

    def test_migration_preserves_exact_metadata_and_never_promotes(self):
        value = copy.deepcopy(self.legacy)
        entry = value["skills"][0]
        entry["limitations"].append("Unknown individual author; 名 attribution retained")
        entry["evidence"].append({"kind": "review", "reference": "legacy review assertion",
                                  "summary": "Original unbound evidence", "date": "2026-10-18"})
        entry["trust"] = "reviewed"
        original = copy.deepcopy(value)
        proposal = self.new.migrate_registry(value)
        self.assertEqual(value, original)
        self.assertEqual(proposal["source"], original)
        self.assertEqual(proposal["records"][0]["value"]["metadata"], entry)
        self.assertEqual(proposal["source_sha256"], hashlib.sha256(self.new.canonical(value)).hexdigest())
        self.assertEqual(proposal["source_encoding"], "canonical-utf8")
        self.assertFalse(proposal["ready_for_validation"])
        self.assertTrue(proposal["validation_issues"])
        record = proposal["records"][0]["value"]
        self.assertEqual(record["metadata"]["trust"], "reviewed")
        self.assertEqual(record["verification"]["status"], "unverified")
        self.assertIsNone(record["verification"]["manifest_sha256"])
        self.assertTrue(record["verification"]["unknowns"])
        self.assertTrue(record["runtime"]["unknowns"])
        proposal["source"]["skills"][0]["limitations"].append("changed proposal")
        record["metadata"]["evidence"].clear()
        self.assertEqual(value, original)

    def test_candidate_migration_wrapper_retains_legacy_acceptance(self):
        proposal = self.new.migrate_registry(self.legacy)
        self.assertTrue(proposal["ready_for_validation"], proposal["validation_issues"])
        for original, wrapped in zip(self.legacy["skills"], proposal["records"]):
            self.assertEqual(original, wrapped["value"]["metadata"])
            self.old.registry({"schema_version": 1, "skills": [wrapped["value"]["metadata"]]})
            self.new.registry_record(wrapped["value"])

    def test_cli_and_core_are_read_only_and_migration_is_json(self):
        index_path = self.write(self.root / "index.json", self.index([self.record()]))
        legacy_path = self.write(self.root / "legacy.json", self.legacy)
        before = self.snapshot(self.root)
        package_before = self.snapshot(PACKAGE / "registry")
        self.new.registry_file(index_path)
        self.new.migrate_registry(self.legacy)
        valid = self.cli(["registry", index_path])
        self.assertEqual((valid.returncode, valid.stdout.strip(), valid.stderr), (0, b"OK registry", b""))
        result = self.cli(["registry", legacy_path, "--migration-proposal"])
        self.assertEqual((result.returncode, result.stderr), (0, b""))
        self.assertEqual(json.loads(result.stdout), self.new.migrate_registry(self.legacy))
        self.assertEqual(before, self.snapshot(self.root))
        self.assertEqual(package_before, self.snapshot(PACKAGE / "registry"))
        self.assertEqual(LEGACY.read_bytes(), self.original_bytes)

    def test_core_never_fetches_spawns_or_executes_candidate_text(self):
        record = self.record()
        record["metadata"]["installation"]["instructions"] = "__import__('os').system('malicious-command')"
        record["metadata"]["description"] = "$(malicious-command); import subprocess"
        path = self.write(self.root / "index.json", self.index([record]))
        with mock.patch("socket.socket", side_effect=AssertionError("network attempted")), \
             mock.patch("subprocess.Popen", side_effect=AssertionError("process attempted")), \
             mock.patch("os.system", side_effect=AssertionError("shell attempted")), \
             mock.patch("builtins.eval", side_effect=AssertionError("eval attempted")), \
             mock.patch("builtins.exec", side_effect=AssertionError("exec attempted")):
            self.new.registry_file(path)
            self.new.registry_record(record)
            self.new.migrate_registry(self.legacy)

    def test_production_exact_three_records_and_legacy_unchanged(self):
        index_path = PACKAGE / "registry/index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        self.assertEqual({item["id"] for item in index["records"]},
                         {"openai-gh-fix-ci", "anthropic-frontend-design", "vercel-react-best-practices"})
        self.assertEqual(len(index["records"]), 3)
        before = self.snapshot(PACKAGE / "registry")
        self.new.registry_file(index_path)
        originals = {item["id"]: item for item in self.legacy["skills"]}
        for reference in index["records"]:
            record = json.loads((index_path.parent / reference["path"]).read_text(encoding="utf-8"))
            self.assertEqual(record["metadata"]["trust"], "candidate")
            if reference["id"] in originals:
                self.assertEqual(record["metadata"], originals[reference["id"]])
            if reference["id"] == "vercel-react-best-practices":
                self.assertIn("react-best-practices", record["aliases"])
        self.assertEqual(before, self.snapshot(PACKAGE / "registry"))
        self.assertEqual(LEGACY.read_bytes(), self.original_bytes)


if __name__ == "__main__":
    unittest.main()
