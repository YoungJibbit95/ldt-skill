"""Differential checks against the immutable pre-M1a executable.

The oracle is deliberately the old source, not expectations copied from the
extracted implementation. The existing regression suite covers platform mocks.
"""
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
PACKAGE = REPO / ".agents/skills/architect-dev-team"
SCRIPT = PACKAGE / "scripts/validate.py"
BASELINE = REPO / "tests/fixtures/m1a-baseline/validate.py"
TEMP_ROOT = Path(tempfile.gettempdir())


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Equivalence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = load(BASELINE, "m1a_baseline")
        cls.new = load(SCRIPT, "m1a_facade")
        # Direct file-path loading must expose the adjacent canonical package.
        import ldt_core
        cls.core = ldt_core

    def setUp(self):
        TEMP_ROOT.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=TEMP_ROOT)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / ".architect-dev-team").mkdir()
        (self.root / "app.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        (self.root / "名.py").write_text("value = 1\n", encoding="utf-8")
        self.architecture = self.root / ".architect-dev-team/architecture.md"
        self.architecture.write_text("# A1\nCalculator.\n", encoding="utf-8")
        self.path = self.root / ".architect-dev-team/state.json"
        self.value = {
            "schema_version": 2, "phase": "INTAKE", "approval_stage": None,
            "profile": "lean", "architecture": None, "milestone": None,
            "approvals": [], "checks": [], "review": None, "completed": [],
            "open_issues": [], "constraints": [], "next_action": "Discover behavior",
        }
        self.env = dict(os.environ, TEMP=str(TEMP_ROOT), TMP=str(TEMP_ROOT),
                        PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="cp1252")

    def run_cli(self, script, args):
        return subprocess.run([sys.executable, "-B", str(script), *map(str, args)],
                              cwd=self.root, env=self.env, capture_output=True)

    def cli_equal(self, args, expected):
        old = self.run_cli(BASELINE, args)
        new = self.run_cli(SCRIPT, args)
        self.assertEqual((old.returncode, old.stdout, old.stderr),
                         (new.returncode, new.stdout, new.stderr), args)
        self.assertEqual(old.returncode, expected, old.stderr)
        return old

    def write_state(self, value=None):
        self.path.write_text(json.dumps(self.value if value is None else value,
                                        ensure_ascii=False), encoding="utf-8")

    def decision(self, kind):
        return {"kind": kind, "decision": "approved",
                "scope_sha256": self.old.scope(self.value),
                "review_sha256": self.value["review"]["sha256"] if kind == "iteration" else None,
                "evidence": "user message 42: approve M1", "recorded_at": "2026-10-18T17:00:00+02:00"}

    def ready_review(self):
        self.value["architecture"] = {"path": ".architect-dev-team/architecture.md",
                                      "sha256": self.old.digest_file(self.architecture)}
        self.value["milestone"] = {"id": "M1", "summary": "Add integers",
                                   "acceptance": ["2+3=5"], "required_checks": ["acceptance"]}
        self.value["checks"] = [{"name": "acceptance", "required": True,
                                 "status": "passed", "evidence": "assertion passed", "waiver": None}]
        self.value["approvals"] = [self.decision("architecture")]
        review = self.root / ".architect-dev-team/review.json"
        review.write_bytes(self.old.canonical(self.old.snapshot(self.root)))
        self.value["review"] = {"path": ".architect-dev-team/review.json",
                                "sha256": self.old.digest_file(review),
                                "independence": "self", "evidence": "source and assertion reviewed"}

    def test_oracle_artifacts_match_approved_manifest(self):
        manifest = json.loads((REPO / "design/v2-proposal-manifest.json").read_text(encoding="utf-8"))
        pinned = {item["path"]: item["sha256"] for item in manifest["current_implementation_baseline"]}
        for fixture, original in ((BASELINE, ".agents/skills/architect-dev-team/scripts/validate.py"),
                                  (BASELINE.with_name("test_validate.py"), "tests/test_validate.py")):
            with self.subTest(artifact=original):
                self.assertEqual(hashlib.sha256(fixture.read_bytes()).hexdigest(), pinned[original])

    def test_cli_help_and_parser_diagnostics(self):
        for args, code in [([], 2), (["--help"], 0), (["unknown"], 2),
                           (["state", "x"], 2), (["state", "x", "--root", ".", "--gate", "bad"], 2),
                           (["digest"], 2), (["snapshot", ".", "--extra"], 2)]:
            with self.subTest(args=args):
                self.cli_equal(args, code)
        for command in ("package", "registry", "digest", "scope", "state", "migrate-state", "snapshot"):
            with self.subTest(help=command):
                if command == "registry":
                    # M1b adds one explicit proposal flag to this existing helper.
                    result = self.run_cli(SCRIPT, [command, "--help"])
                    self.assertEqual((result.returncode, result.stderr), (0, b""))
                    self.assertIn(b"--migration-proposal", result.stdout)
                else:
                    self.cli_equal([command, "--help"], 0)

    def test_cli_all_commands_and_no_writes(self):
        self.write_state()
        registry = self.root / ".architect-dev-team/registry.json"
        registry.write_text('{"schema_version":1,"skills":[]}', encoding="utf-8")
        legacy = copy.deepcopy(self.value)
        legacy["schema_version"] = 1
        legacy_path = self.root / ".architect-dev-team/legacy.json"
        legacy_path.write_text(json.dumps(legacy), encoding="utf-8")
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        for args in (["digest", self.architecture], ["scope", self.path],
                     ["registry", registry], ["package", PACKAGE],
                     ["snapshot", self.root], ["state", self.path, "--root", self.root],
                     ["migrate-state", legacy_path, "--root", self.root]):
            with self.subTest(command=args[0]):
                self.cli_equal(args, 0)
        self.assertEqual(before, {p.relative_to(self.root): p.read_bytes()
                                 for p in self.root.rglob("*") if p.is_file()})

    def test_cli_gate_and_adversarial_state_parity(self):
        self.ready_review()
        approved = copy.deepcopy(self.value)
        for gate in ("implement", "review"):
            self.write_state()
            self.cli_equal(["state", self.path, "--root", self.root, "--gate", gate], 0)
        self.value["approvals"].append(self.decision("iteration"))
        self.write_state()
        self.cli_equal(["state", self.path, "--root", self.root, "--gate", "advance"], 0)
        variants = []
        def variant(label, edit):
            value = copy.deepcopy(approved)
            edit(value)
            variants.append((label, value))
        variant("missing approval", lambda v: v.update(approvals=[]))
        variant("rejection supersedes", lambda v: v["approvals"].append(dict(v["approvals"][0], decision="rejected")))
        variant("scope changed", lambda v: v["milestone"].update(summary="changed"))
        variant("demoted required check", lambda v: v["checks"][0].update(required=False))
        variant("duplicate policy", lambda v: v["milestone"]["required_checks"].append("acceptance"))
        variant("failed check", lambda v: v["checks"][0].update(status="failed"))
        variant("forged waiver", lambda v: v["checks"][0].update(status="waived", waiver={
            "evidence": "user message 99", "reason": "unavailable", "scope_sha256": "0" * 64}))
        variant("waiver on failed check", lambda v: v["checks"][0].update(status="failed", waiver={
            "evidence": "user message 99", "reason": "unavailable", "scope_sha256": self.old.scope(v)}))
        def rigorous(value):
            value["profile"] = "rigorous"
            value["approvals"][0]["scope_sha256"] = self.old.scope(value)
        variant("review independence", rigorous)
        variant("path escape", lambda v: v["architecture"].update(path="../名.py"))
        variant("NUL path", lambda v: v["architecture"].update(path="bad\x00.py"))
        variant("wrong schema type", lambda v: v.update(schema_version=True))
        for label, value in variants:
            with self.subTest(case=label):
                self.write_state(value)
                self.cli_equal(["state", self.path, "--root", self.root, "--gate", "review"], 1)
        self.value = approved
        self.value["checks"][0].update(status="waived", waiver={
            "evidence": "user message 99", "reason": "runner unavailable", "scope_sha256": self.old.scope(self.value)})
        self.write_state()
        self.cli_equal(["state", self.path, "--root", self.root, "--gate", "review"], 0)
        (self.root / "app.py").write_text("changed\n", encoding="utf-8")
        self.cli_equal(["state", self.path, "--root", self.root, "--gate", "review"], 1)
        # A self-consistent hash cannot bless an incomplete review manifest.
        review = self.root / self.value["review"]["path"]
        manifest = self.old.snapshot(self.root)
        manifest["files"] = []
        review.write_bytes(self.old.canonical(manifest))
        self.value["review"]["sha256"] = self.old.digest_file(review)
        self.write_state()
        self.cli_equal(["state", self.path, "--root", self.root, "--gate", "review"], 1)

    def test_cli_json_and_missing_path_failures(self):
        for raw in (b'{"a":1,"a":2}', b'{"x":NaN}', b'{"x":Infinity}', b'\xff', b'{', b' ' * 65537):
            self.path.write_bytes(raw)
            with self.subTest(raw=raw[:30]):
                self.cli_equal(["state", self.path, "--root", self.root], 1)
        for args in (["digest", self.root / "absent"], ["snapshot", self.root / "absent"],
                     ["registry", self.path], ["migrate-state", self.path, "--root", self.root]):
            with self.subTest(command=args[0]):
                self.cli_equal(args, 1)

    def test_function_surface_and_core_outcomes(self):
        tree = ast.parse(BASELINE.read_text(encoding="utf-8"))
        names = [node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))]
        for name in names:
            with self.subTest(export=name):
                self.assertTrue(callable(getattr(self.new, name)))
                if name != "main":  # CLI presentation remains in the facade.
                    self.assertIs(getattr(self.new, name), getattr(self.core, name))
        for name in ("PHASES", "MANAGED", "WALK_IGNORED"):
            self.assertEqual(getattr(self.old, name), getattr(self.core, name))
        self.ready_review()
        self.write_state()
        cases = [("canonical", ({"z": "名", "a": [True, None]},)),
                 ("digest_bytes", (b"\x00\xff",)), ("digest_file", (self.architecture,)),
                 ("scope", (self.value,)), ("scope_fields", (self.value,)),
                 ("snapshot", (self.root,)), ("state", (self.value, self.root, "review")),
                 ("approval", (self.value, "iteration")),
                 ("relative", ("../escape",)), ("path_text", ("bad\x00",)),
                 ("local_file", (self.root, "absent")), ("read_json", (self.path, 4)),
                 ("registry", ({"schema_version": 1, "skills": []},)),
                 ("timestamp", ("2026-10-18T17:00:00",)),
                 ("unique_object", ([("a", 1), ("a", 2)],))]
        def outcome(module, name, args):
            try:
                return ("return", getattr(module, name)(*copy.deepcopy(args)))
            except Exception as exc:
                return ("raise", type(exc).__name__, str(exc))
        for name, args in cases:
            expected = outcome(self.old, name, args)
            for module in (self.new, self.core):
                with self.subTest(function=name, module=module.__name__):
                    self.assertEqual(expected, outcome(module, name, args))

    def test_relocated_direct_import_preserves_embedding_streams_and_cwd(self):
        relocated = self.root / "relocated skill"
        shutil.copytree(PACKAGE / "scripts", relocated / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        probe = r'''
import importlib.util, io, os, sys
from pathlib import Path
class Stream(io.StringIO):
    def reconfigure(self, **kwargs):
        raise AssertionError("import reconfigured embedding stream")
out, err = Stream(), Stream()
sys.stdout, sys.stderr = out, err
cwd = os.getcwd()
if len(sys.argv) > 2 and sys.argv[2] == "core-first":
    core_spec = importlib.util.spec_from_file_location("ldt_core", Path(sys.argv[1]).parent / "ldt_core/__init__.py")
    core = importlib.util.module_from_spec(core_spec)
    sys.modules["ldt_core"] = core
    core_spec.loader.exec_module(core)
spec = importlib.util.spec_from_file_location("embedded_validator", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert sys.stdout is out and sys.stderr is err
assert os.getcwd() == cwd
assert out.getvalue() == err.getvalue() == ""
assert module.digest_bytes(b"x") == "2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881"
if len(sys.argv) > 2:
    import ldt_core
    assert module.state is ldt_core.state
    assert module.Invalid is ldt_core.Invalid
'''
        for path, extra in ((BASELINE, []), (relocated / "scripts/validate.py", ["core"]),
                            (relocated / "scripts/validate.py", ["core-first"])):
            result = subprocess.run([sys.executable, "-B", "-c", probe, str(path), *extra],
                                    cwd=self.root, env=self.env, capture_output=True)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b"", b""))
        old = self.run_cli(BASELINE, ["--help"])
        new = self.run_cli(relocated / "scripts/validate.py", ["--help"])
        self.assertEqual((old.returncode, old.stdout, old.stderr), (new.returncode, new.stdout, new.stderr))

    def test_missing_core_files_are_justified_package_completeness_difference(self):
        # Extraction adds runtime files. The historical monolith accepted their
        # absence; accepting an unexecutable extracted package would be a bug.
        relocated = self.root / "package completeness"
        shutil.copytree(PACKAGE, relocated,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        core_files = ("__init__.py", "common.py", "snapshots.py", "approvals.py",
                      "state.py", "registry.py", "package.py")
        for filename in core_files:
            path = relocated / "scripts/ldt_core" / filename
            original = path.read_bytes()
            path.unlink()
            try:
                with self.subTest(missing=filename):
                    old = self.run_cli(BASELINE, ["package", relocated])
                    self.assertEqual((old.returncode, old.stdout, old.stderr), (0, b"OK package\r\n" if os.name == "nt" else b"OK package\n", b""))
                    new = self.run_cli(SCRIPT, ["package", relocated])
                    self.assertEqual(new.returncode, 1, new.stderr)
                    self.assertEqual(new.stdout, b"")
                    self.assertIn(("missing file: scripts/ldt_core/" + filename).encode(), new.stderr)
                    with self.assertRaisesRegex(self.core.Invalid, "missing file"):
                        self.core.package(relocated)
            finally:
                path.write_bytes(original)

    def test_two_relocated_facades_keep_each_adjacent_core(self):
        copies = [self.root / "copy one", self.root / "copy two"]
        for copy_path in copies:
            shutil.copytree(PACKAGE / "scripts", copy_path,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        probe = r'''
import importlib.util, io, os, sys
from pathlib import Path
class Stream(io.StringIO):
    def reconfigure(self, **kwargs):
        raise AssertionError("import reconfigured embedding stream")
out, err = Stream(), Stream()
sys.stdout, sys.stderr = out, err
cwd, search_path = os.getcwd(), list(sys.path)
modules = []
for number, script in enumerate(sys.argv[1:]):
    spec = importlib.util.spec_from_file_location("embedded_copy_" + str(number), script)
    facade = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(facade)
    common = sys.modules[facade.Invalid.__module__]
    core = sys.modules[common.__package__]
    assert Path(core.__file__).resolve() == Path(script).resolve().parent / "ldt_core/__init__.py"
    assert facade.Invalid is core.Invalid
    assert facade.state is core.state
    assert facade.require is core.require
    try:
        facade.require(False, "per-copy exception")
    except facade.Invalid as exc:
        assert type(exc) is core.Invalid and str(exc) == "per-copy exception"
    else:
        raise AssertionError("validation did not fail")
    assert sys.stdout is out and sys.stderr is err
    assert os.getcwd() == cwd and sys.path == search_path
    assert out.getvalue() == err.getvalue() == ""
    modules.append((facade, core))
assert modules[0][1] is sys.modules["ldt_core"]
assert modules[0][1] is not modules[1][1]
assert modules[0][0].Invalid is not modules[1][0].Invalid
assert modules[0][0].state is not modules[1][0].state
assert modules[0][0].digest_bytes(b"x") == modules[1][0].digest_bytes(b"x")
'''
        result = subprocess.run([sys.executable, "-B", "-c", probe,
                                 *[str(path / "validate.py") for path in copies]],
                                cwd=self.root, env=self.env, capture_output=True)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b"", b""))

    def test_foreign_namespace_package_does_not_shadow_adjacent_core(self):
        probe = r'''
import importlib.util, sys, types
foreign = types.ModuleType("ldt_core")
foreign.__file__ = None
foreign.__path__ = []
sys.modules["ldt_core"] = foreign
spec = importlib.util.spec_from_file_location("embedded_validator", sys.argv[1])
facade = importlib.util.module_from_spec(spec)
spec.loader.exec_module(facade)
assert sys.modules["ldt_core"] is foreign
assert facade.Invalid.__module__.startswith("_architect_dev_team_core_")
assert facade.digest_bytes(b"x") == "2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881"
try:
    facade.require(False, "adjacent validation")
except facade.Invalid as exc:
    assert str(exc) == "adjacent validation"
else:
    raise AssertionError("validation did not reject")
'''
        result = subprocess.run([sys.executable, "-B", "-c", probe, str(SCRIPT)],
                                cwd=self.root, env=self.env, capture_output=True)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b"", b""))


if __name__ == "__main__":
    unittest.main()
