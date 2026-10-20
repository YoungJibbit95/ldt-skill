"""Independent M1c acceptance checks for the bounded read-only inventory API."""
import importlib
import json
import os
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
import socket
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / ".agents/skills/architect-dev-team/scripts"
sys.path.insert(0, str(SCRIPTS))
from ldt_core.common import Invalid


class InventoryAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = importlib.import_module("ldt_core.inventory")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, relative, content=""):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        return path

    def scan(self):
        return self.module.inventory(self.root)

    def facts(self, result):
        return result["observations"] + result["inferences"]

    def assert_schema(self, result):
        self.assertEqual(set(result), {"output_version", "observations", "inferences",
                                      "capability_needs", "unknowns", "coverage"})
        self.assertEqual(result["output_version"], 1)
        for field in ("observations", "inferences"):
            self.assertIsInstance(result[field], list)
            for fact in result[field]:
                self.assertEqual(set(fact), {"kind", "value", "evidence"})
                self.assertEqual(set(fact["evidence"]), {"path", "signal"})
                for value in (fact["kind"], fact["value"], fact["evidence"]["signal"]):
                    self.assertIsInstance(value, str)
                self.assert_relative(fact["evidence"]["path"])
        for need in result["capability_needs"]:
            self.assertEqual(set(need), {"need", "status", "evidence"})
            self.assertEqual(need["status"], "inferred")
            for path in need["evidence"]:
                self.assert_relative(path)
        self.assertTrue(result["unknowns"])
        self.assertTrue(all(isinstance(item, str) for item in result["unknowns"]))
        coverage = result["coverage"]
        self.assertEqual(set(coverage), {"complete", "policy", "limits", "issues", "excluded",
                                         "directories_scanned", "files_read"})
        self.assertIs(coverage["complete"], False)
        self.assertTrue(coverage["policy"])
        self.assertTrue(coverage["limits"])
        for issue in coverage["issues"]:
            self.assertEqual(set(issue), {"path", "reason"})
            self.assert_relative(issue["path"])
            self.assertTrue(issue["reason"])
        json.dumps(result, allow_nan=False)

    def assert_relative(self, path):
        self.assertIsInstance(path, str)
        self.assertFalse(PurePosixPath(path).is_absolute())
        self.assertNotIn("\\", path)
        self.assertNotIn(":", path)
        self.assertNotIn("..", path.split("/"))

    def assert_issue(self, result, relative):
        self.assertTrue(any(issue["path"] == relative for issue in result["coverage"]["issues"]), result)

    def snapshot(self):
        return {path.relative_to(self.root).as_posix():
                (path.is_dir(), path.stat().st_mtime_ns, None if path.is_dir() else path.read_bytes())
                for path in [self.root, *self.root.rglob("*")]}

    def test_empty_non_git_directory_has_explicit_uncertainty(self):
        result = self.scan()
        self.assert_schema(result)
        self.assertEqual(result, self.scan())
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_realistic_monorepo_evidence_and_private_values(self):
        self.put("package.json", json.dumps({"name": "PRIVATE_PROJECT_SENTINEL", "version": "PRIVATE_VERSION",
                 "scripts": {"test": "PRIVATE_SCRIPT"}, "repository": "https://PRIVATE_REMOTE.invalid",
                 "dependencies": {"react": "PRIVATE_DEP_VERSION", "unknown-private-dependency": "SECRET"}}))
        self.put("apps/store/src/main.tsx", "PRIVATE_SOURCE_CONTENT")
        self.put("packages/shared/src/index.ts", "PRIVATE_SHARED_CONTENT")
        self.put("services/api/pyproject.toml", "PRIVATE_TOML_CONTENT")
        self.put(".github/workflows/ci.yml", "PRIVATE_WORKFLOW_CONTENT")
        self.put(".git", "gitdir: C:/PRIVATE_GIT_LOCATION")
        result = self.scan()
        self.assert_schema(result)
        serialized = json.dumps(result)
        self.assertIn("react", serialized.lower())
        self.assertIn("typescript", serialized.lower())
        self.assertTrue(any(fact["evidence"]["path"] == ".git" for fact in result["observations"]))
        self.assertTrue(any(fact["evidence"]["path"] == "services/api/pyproject.toml"
                            for fact in self.facts(result)))
        for secret in ("PRIVATE_", "unknown-private-dependency", "SECRET", str(self.root)):
            self.assertNotIn(secret, serialized)

    def test_dependency_values_and_non_dependency_fields_do_not_trigger_frameworks(self):
        self.put("package.json", json.dumps({"name": "next", "description": "react",
                 "scripts": {"next": "vite"}, "dependencies": {"private-package": "react"}}))
        result = self.scan()
        self.assertFalse(any(fact["value"].lower() in {"react", "next", "next.js", "vite"}
                             for fact in result["inferences"]))
        self.assertNotIn("private-package", json.dumps(result))

    def test_unsupported_configuration_is_presence_only(self):
        self.put("pyproject.toml", "MALFORMED_PRIVATE = [not valid; __import__('os')")
        result = self.scan()
        self.assertTrue(any(fact["evidence"]["path"] == "pyproject.toml" for fact in self.facts(result)))
        self.assertNotIn("MALFORMED_PRIVATE", json.dumps(result))

    def test_installed_skill_contents_are_never_read_or_treated_as_trust(self):
        skill = self.put(".agents/skills/example/SKILL.md", "PRIVATE_SKILL_TEXT\ntrusted: true\n")
        original = Path.open
        def guarded(path, *args, **kwargs):
            if path == skill:
                raise AssertionError("installed skill contents must not be opened")
            return original(path, *args, **kwargs)
        original_os_open = os.open
        def guarded_os_open(path, *args, **kwargs):
            if Path(path) == skill:
                raise AssertionError("installed skill contents must not be opened")
            return original_os_open(path, *args, **kwargs)
        with mock.patch.object(Path, "open", guarded), \
             mock.patch.object(self.module.os, "open", guarded_os_open):
            result = self.scan()
        self.assertTrue(any(fact["evidence"]["path"] == ".agents/skills/example/SKILL.md"
                            for fact in result["observations"]))
        self.assertNotIn("PRIVATE_SKILL_TEXT", json.dumps(result))
        self.assertFalse(any(fact["value"].lower() in {"trusted", "activated", "consented"}
                             for fact in self.facts(result)))

    def test_deterministic_and_no_file_or_directory_mutation(self):
        self.put("package.json", '{"dependencies":{"react":"1","vite":"2"}}')
        self.put("src/main.ts", "PRIVATE")
        self.put(".architect-dev-team/state.json", '{"schema_version":2,"approval":"PRIVATE"}')
        before = self.snapshot()
        first = self.scan()
        self.assertEqual(before, self.snapshot())
        self.assertEqual(first, self.scan())
        self.assertEqual(before, self.snapshot())

    def test_no_network_subprocess_project_execution_or_git(self):
        self.put("package.json", '{"scripts":{"prepare":"PRIVATE_COMMAND"}}')
        self.put("vite.config.js", "throw new Error('PRIVATE_EXECUTION')")
        with mock.patch.object(subprocess, "run", side_effect=AssertionError("subprocess forbidden")), \
             mock.patch.object(subprocess, "Popen", side_effect=AssertionError("process forbidden")), \
             mock.patch.object(os, "system", side_effect=AssertionError("shell forbidden")), \
             mock.patch.object(socket, "socket", side_effect=AssertionError("network forbidden")):
            result = self.scan()
        self.assertNotIn("PRIVATE_EXECUTION", json.dumps(result))

    def test_missing_and_file_roots_raise_shared_invalid(self):
        for root in (self.root / "missing", self.put("plain-file")):
            with self.subTest(root=root), self.assertRaises(Invalid):
                self.module.inventory(root)

    def test_malformed_json_bytes_and_shapes_are_coverage_issues(self):
        for content in (b"{", b"\xff", b"[]", b'{"dependencies":[]}',
                        b'{"dependencies":{"react":"1"},"dependencies":{"vite":"1"}}'):
            with self.subTest(content=content):
                self.put("package.json", content)
                result = self.scan()
                self.assert_schema(result)
                self.assert_issue(result, "package.json")

    def test_unreadable_manifest_discloses_coverage_without_os_exception_text(self):
        target = self.put("package.json", "{}")
        original = os.open
        def guarded(path, *args, **kwargs):
            if Path(path) == target:
                raise PermissionError("PRIVATE_ABSOLUTE_ERROR " + str(self.root))
            return original(path, *args, **kwargs)
        with mock.patch.object(self.module.os, "open", guarded):
            result = self.scan()
        self.assert_issue(result, "package.json")
        self.assertNotIn("PRIVATE_ABSOLUTE_ERROR", json.dumps(result))
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_oversized_manifest_is_bounded_and_reported(self):
        self.put("package.json", b" " * (4 * 1024 * 1024))
        result = self.scan()
        self.assert_issue(result, "package.json")
        self.assertLess(len(json.dumps(result)), 100000)

    def test_non_allowlisted_directories_are_not_inspected(self):
        self.put("node_modules/react/package.json", '{"dependencies":{"next":"1"}}')
        self.put("private-data/package.json", '{"dependencies":{"next":"1"}}')
        self.put(".env", "PRIVATE_CREDENTIAL")
        result = self.scan()
        self.assertFalse(any(fact["evidence"]["path"].startswith(("node_modules/", "private-data/"))
                             for fact in self.facts(result)))
        self.assertNotIn("PRIVATE_CREDENTIAL", json.dumps(result))
        self.assertTrue(result["coverage"]["excluded"])

    def test_symlink_manifest_and_directory_are_not_followed(self):
        with tempfile.TemporaryDirectory() as external:
            external = Path(external)
            (external / "package.json").write_text('{"dependencies":{"next":"1"}}', encoding="utf-8")
            try:
                (self.root / "package.json").symlink_to(external / "package.json")
                (self.root / "src").symlink_to(external, target_is_directory=True)
            except OSError as exc:
                self.skipTest("Native symlink creation unavailable: " + type(exc).__name__)
            result = self.scan()
            self.assert_issue(result, "package.json")
            self.assert_issue(result, "src")
            self.assertFalse(any(fact["value"].lower() in {"next", "next.js"}
                                 for fact in result["inferences"]))

    def test_deep_allowed_structure_has_explicit_bound(self):
        relative = "/".join(["src"] * 40) + "/package.json"
        self.put(relative, '{"dependencies":{"react":"1"}}')
        result = self.scan()
        self.assertTrue(result["coverage"]["issues"])
        self.assertFalse(any(fact["evidence"]["path"] == relative for fact in self.facts(result)))

    def test_inaccessible_directory_is_reported_without_leaking_exception(self):
        self.put("src/main.py", "PRIVATE")
        original = os.scandir
        def guarded(path):
            if Path(path) == self.root / "src":
                raise PermissionError("PRIVATE_DIRECTORY_ERROR " + str(self.root))
            return original(path)
        with mock.patch.object(self.module.os, "scandir", guarded):
            result = self.scan()
        self.assert_issue(result, "src")
        self.assertNotIn("PRIVATE_DIRECTORY_ERROR", json.dumps(result))

    def test_sensitive_and_unsafe_names_are_omitted_with_coverage_issue(self):
        self.put("apps/private-token-value/package.json", '{"dependencies":{"next":"1"}}')
        self.put("apps/unsafe name/package.json", '{"dependencies":{"next":"1"}}')
        result = self.scan()
        self.assertTrue(result["coverage"]["issues"])
        for private_name in ("private-token-value", "unsafe name"):
            self.assertNotIn(private_name, json.dumps(result))

    def test_directory_entry_budget_reports_incomplete_coverage(self):
        # A fixture exceeds the documented budget while remaining small on disk.
        for number in range(self.module.LIMITS["entries_per_directory"] + 1):
            self.put("src/file_" + str(number) + ".ts")
        result = self.scan()
        self.assert_issue(result, "src")
        self.assertEqual(result, self.scan())

    def test_json_recursion_and_invalid_dependency_values_are_safe(self):
        for content in ('{"dependencies":{"react":{"private":"secret"}}}',
                        '{"dependencies":{"react":NaN}}'):
            with self.subTest(content=content[:60]):
                self.put("package.json", content)
                result = self.scan()
                self.assert_issue(result, "package.json")
                self.assertNotIn("secret", json.dumps(result))

    def test_deep_json_has_safe_output_on_platform_specific_recursion_limits(self):
        self.put("package.json", '{"x":' + '[' * 1500 + '0' + ']' * 1500 + '}')
        result = self.scan()
        # Python builds differ in recursion limits; safe rejection or omission of
        # the irrelevant field is acceptable, but propagating RecursionError is not.
        self.assert_schema(result)
        self.assertLess(len(json.dumps(result)), 10000)

    def test_only_package_json_contents_are_opened(self):
        self.put("package.json", "{}")
        for relative in (".git", "pyproject.toml", "vite.config.js", "src/main.ts",
                         ".env", ".agents/skills/example/SKILL.md"):
            self.put(relative, "PRIVATE_MUST_NOT_BE_READ")
        original_os_open = os.open
        original_path_open = Path.open
        def check(path):
            if Path(path).is_relative_to(self.root):
                self.assertEqual(Path(path), self.root / "package.json", "unexpected file read")
        def os_guard(path, *args, **kwargs):
            check(path)
            return original_os_open(path, *args, **kwargs)
        def path_guard(path, *args, **kwargs):
            check(path)
            return original_path_open(path, *args, **kwargs)
        with mock.patch.object(self.module.os, "open", os_guard), \
             mock.patch.object(Path, "open", path_guard):
            result = self.scan()
        self.assertNotIn("PRIVATE_MUST_NOT_BE_READ", json.dumps(result))

    def test_multiple_hard_links_are_not_read(self):
        original = self.put("original-private", '{"dependencies":{"react":"1"}}')
        try:
            os.link(original, self.root / "package.json")
        except OSError as exc:
            self.skipTest("Native hard-link creation unavailable: " + type(exc).__name__)
        result = self.scan()
        self.assert_issue(result, "package.json")
        self.assertFalse(any(fact["value"].lower() == "react" for fact in result["inferences"]))

    def test_simulated_windows_reparse_entries_are_skipped_without_reads(self):
        self.put("package.json", '{"dependencies":{"react":"1"}}')
        self.put("src/main.ts", "PRIVATE_REPARSE_CONTENT")
        real_scandir = os.scandir
        class ReparseEntry:
            def __init__(self, entry):
                self.name, self.path, self.entry = entry.name, entry.path, entry
            def stat(self, *, follow_symlinks=True):
                info = self.entry.stat(follow_symlinks=follow_symlinks)
                # A regular file/directory mode with the Windows reparse bit;
                # S_ISLNK alone cannot detect this mocked junction case.
                return SimpleNamespace(st_mode=info.st_mode,
                                       st_file_attributes=getattr(info, "st_file_attributes", 0) | 0x400)
        @contextmanager
        def scandir(path):
            self.assertEqual(Path(path), self.root, "reparse directory must not be traversed")
            with real_scandir(path) as entries:
                yield (ReparseEntry(entry) for entry in entries)
        with mock.patch.object(self.module.os, "scandir", scandir), \
             mock.patch.object(self.module.os, "open", side_effect=AssertionError("reparse content read")):
            result = self.scan()
        self.assert_schema(result)
        self.assert_issue(result, "package.json")
        self.assert_issue(result, "src")
        self.assertEqual(result["inferences"], [])

    def test_simulated_windows_reparse_root_is_rejected(self):
        real_lstat = Path.lstat
        def lstat(path, *args, **kwargs):
            info = real_lstat(path, *args, **kwargs)
            if path == self.root:
                return SimpleNamespace(st_mode=info.st_mode,
                                       st_file_attributes=getattr(info, "st_file_attributes", 0) | 0x400)
            return info
        with mock.patch.object(Path, "lstat", lstat), \
             mock.patch.object(self.module.os, "scandir", side_effect=AssertionError("reparse root scanned")):
            with self.assertRaises(Invalid):
                self.scan()

    def test_traversal_bearing_enumerated_name_is_rejected_before_stat_or_read(self):
        # Filesystems cannot return this name through ordinary enumeration. The
        # hostile DirEntry fixture checks the input boundary without creating a
        # native traversal filename or accessing anything outside the fixture.
        entry = SimpleNamespace(name="../package.json", path=str(self.root.parent / "package.json"),
                                stat=mock.Mock(side_effect=AssertionError("unsafe entry stat")))
        @contextmanager
        def scandir(path):
            self.assertEqual(Path(path), self.root)
            yield iter([entry])
        with mock.patch.object(self.module.os, "scandir", scandir), \
             mock.patch.object(self.module.os, "open", side_effect=AssertionError("unsafe path read")):
            result = self.scan()
        entry.stat.assert_not_called()
        self.assert_schema(result)
        self.assert_issue(result, ".")
        self.assertNotIn("../package.json", json.dumps(result))

    def test_changed_file_identity_after_read_is_reported_without_inference(self):
        target = self.put("package.json", '{"dependencies":{"react":"1"}}')
        real_lstat = Path.lstat
        calls = []
        def lstat(path, *args, **kwargs):
            info = real_lstat(path, *args, **kwargs)
            if path == target:
                calls.append(path)
                if len(calls) > 1:
                    return SimpleNamespace(st_dev=info.st_dev, st_ino=info.st_ino,
                                           st_mode=info.st_mode, st_size=info.st_size,
                                           st_mtime_ns=info.st_mtime_ns + 1)
            return info
        with mock.patch.object(Path, "lstat", lstat):
            result = self.scan()
        self.assertGreaterEqual(len(calls), 2, "fixture must reach the post-read identity guard")
        self.assert_issue(result, "package.json")
        self.assertFalse(any(fact["value"].lower() == "react" for fact in self.facts(result)))

    def test_total_entry_budget_stops_sibling_enumeration(self):
        for directory in ("src", "tests"):
            for name in ("a.py", "b.py"):
                self.put(directory + "/" + name)
        real_scandir = os.scandir
        opened, yielded = [], []
        class CountingIterator:
            def __init__(self, path):
                opened.append(Path(path))
                self.iterator = real_scandir(path)
            def __enter__(self):
                self.iterator.__enter__()
                return self
            def __exit__(self, *args):
                return self.iterator.__exit__(*args)
            def __iter__(self):
                return self
            def __next__(self):
                entry = next(self.iterator)
                yielded.append(entry.path)
                return entry
        with mock.patch.dict(self.module.LIMITS, {"entries": 4}), \
             mock.patch.object(self.module.os, "scandir", CountingIterator):
            result = self.scan()
        self.assertLessEqual(len(yielded), 4, "global budget must bound successful iterator yields")
        self.assertEqual(opened, [self.root, self.root / "src"],
                         "later siblings must not be opened after budget exhaustion")
        self.assert_issue(result, "src")
        self.assert_issue(result, "tests")

    def test_directory_budget_includes_failed_scan_attempts(self):
        for workspace in ("alpha", "beta", "gamma"):
            self.put("apps/" + workspace + "/package.json", "{}")
        real_scandir = os.scandir
        attempted = []
        def scandir(path):
            path = Path(path)
            attempted.append(path)
            if path.parent == self.root / "apps":
                raise PermissionError("simulated inaccessible workspace")
            return real_scandir(path)
        with mock.patch.dict(self.module.LIMITS, {"directories": 3}), \
             mock.patch.object(self.module.os, "scandir", scandir):
            result = self.scan()
        self.assertLessEqual(len(attempted), 3, "failed attempts must consume the directory budget")
        self.assertEqual(attempted, [self.root, self.root / "apps", self.root / "apps/alpha"])
        self.assertEqual(result["coverage"]["directories_scanned"], 2,
                         "reported scanned count describes successful scans")
        for relative in ("apps/alpha", "apps/beta", "apps/gamma"):
            self.assert_issue(result, relative)
        reasons = {issue["path"]: issue["reason"] for issue in result["coverage"]["issues"]}
        self.assertIn("unreadable", reasons["apps/alpha"].lower())
        self.assertIn("limit", reasons["apps/beta"].lower())


if __name__ == "__main__":
    unittest.main()
