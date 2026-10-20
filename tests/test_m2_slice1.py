"""Focused acceptance tests for M2 Slice 1: Intake → Architecture → Contracts → Pair → Integration."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from contextlib import contextmanager


REPO = Path(__file__).resolve().parents[1]
VALIDATE_PY = REPO / ".agents/skills/architect-dev-team/scripts/validate.py"
# The interpreter that runs the tests must also run the helper. A hard-coded
# path would break every other platform.
PYTHON = sys.executable
SCRIPTS = REPO / ".agents/skills/architect-dev-team/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from ldt_core import approvals as v  # noqa: E402



FIXTURE = {
    "research": {
        "agent": "explore",
        "session_id": "ses_fixture_research",
        "status": "completed",
        "output": json.dumps({
            "sources": [{"name": "Project brief", "type": "internal",
                         "version": "current", "url": "brief.md", "credibility": "high"}],
            "findings": {"specifications": "Layered modules with a clear data store.",
                         "units": [], "tolerances": [], "reference_values": [],
                         "invariants": []},
            "assumptions": [], "conflicts": [], "applicability_limits": [],
            "recommendation": "Use a layered architecture with a registry module.",
            "confidence": "Medium", "blocking_decisions": [],
        }),
    },
    "implementer": {
        "agent": "general",
        "session_id": "ses_fixture_impl",
        "status": "completed",
        "output": json.dumps({
            "status": "completed",
            "changes": [{"path": "src/users.py", "action": "modified", "sha256": "0" * 64}],
            "findings": ["Added duplicate email guard"],
            "evidence": {"unit-tests": "1 passed"},
            "checks": [{"name": "unit-tests", "status": "passed", "evidence": "1 passed"}],
            "risks": [], "unresolved": [], "review_notes": "Ready for review",
        }),
    },
    "critic": {
        "agent": "explore",
        "session_id": "ses_fixture_critic",
        "status": "completed",
        # A conforming CriticReport. The reviewer identity fields are filled in
        # by the orchestrator from the runtime, not by the agent.
        "output": json.dumps({
            "task_id": "critic-001",
            "reviewed_task_id": "impl-001",
            "reviewed_revision": "",
            "reviewer": {
                "session_id": "ses_fixture_critic", "agent": "explore", "model": "fixture-model",
                "execution_mode": "fixture", "verified": False, "read_only_agent": False,
            },
            "coverage": {
                "requirements_checked": ["register rejects a duplicate email"],
                "files_inspected": ["src/users.py"],
                "interfaces_checked": ["register()"],
                "evidence_references": ["src/users.py:12"],
                "checks_run": [{"name": "unit-tests", "result": "passed",
                                "evidence": "1 passed"}],
                "unverified_areas": ["concurrency"],
            },
            "findings": [{"severity": "major", "file": "src/users.py", "line": 12,
                          "issue": "Case-sensitive duplicate check",
                          "reproduction": "register('A@x.com') then register('a@x.com')",
                          "reference": "acceptance: rejects duplicate email"}],
            "verified_non_findings": ["invalid email is rejected"],
            "confidence": "medium",
            "limitations": ["fixture run"],
            "recommendation": "approve_with_findings",
            "summary": "One major finding on the case-sensitive duplicate check.",
        }),
    },
}


@contextmanager
def runtime_fixture():
    """Enable the explicit, labelled runtime fixture for the current process tree."""
    with tempfile.TemporaryDirectory() as tmp:
        fixture_path = Path(tmp) / "fixture.json"
        fixture_path.write_text(json.dumps(FIXTURE), encoding="utf-8")
        previous = os.environ.get("LDT_RUNTIME_FIXTURE")
        os.environ["LDT_RUNTIME_FIXTURE"] = str(fixture_path)
        try:
            yield
        finally:
            if previous is None:
                os.environ.pop("LDT_RUNTIME_FIXTURE", None)
            else:
                os.environ["LDT_RUNTIME_FIXTURE"] = previous


def run_validate(root: Path, command: str, *args) -> subprocess.CompletedProcess:
    """Run validate.py command and return result.
    CLI expects: validate.py <command> <root> <subcommand> [options...]
    """
    cmd = [PYTHON, str(VALIDATE_PY), command, str(root), *args]
    return subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=60)


class TestIntake(unittest.TestCase):
    """Test automated project intake."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self._init_git()

    def tearDown(self):
        self.temp.cleanup()

    def _init_git(self):
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.test"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.root, check=True)
        (self.root / "README.md").write_text("# Test\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=self.root, check=True)

    def test_intake_creates_versioned_brief(self):
        """Vague project produces versioned brief with open decisions."""
        result = run_validate(self.root, "intake")
        self.assertEqual(result.returncode, 0, result.stderr)

        brief_path = self.root / ".architect-dev-team" / "brief.md"
        self.assertTrue(brief_path.exists())

        content = brief_path.read_text(encoding="utf-8")
        self.assertIn("Project Brief:", content)
        self.assertIn("Open Decisions", content)
        self.assertIn("goals.audience", content)  # Critical gaps identified
        self.assertIn("goals.problem", content)
        self.assertIn("goals.success", content)
        self.assertIn("scope_in", content)

    def test_intake_discovers_stack(self):
        """Discovery identifies Python from pyproject.toml."""
        (self.root / "pyproject.toml").write_text('[project]\nname="test"\nversion="0.1"\n', encoding="utf-8")
        subprocess.run(["git", "add", "pyproject.toml"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "add pyproject"], cwd=self.root, check=True)

        result = run_validate(self.root, "intake")
        self.assertEqual(result.returncode, 0)

        brief_path = self.root / ".architect-dev-team" / "brief.md"
        content = brief_path.read_text(encoding="utf-8")
        self.assertIn("Python", content)


class TestArchitectureTeam(unittest.TestCase):
    """Test architecture team decomposition and research."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self._init_git()
        # Create minimal brief first
        run_validate(self.root, "intake")

    def tearDown(self):
        self.temp.cleanup()

    def _init_git(self):
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.test"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.root, check=True)
        (self.root / "README.md").write_text("# Test\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=self.root, check=True)

    def test_decompose_creates_research_tasks(self):
        """Decompose creates 4 research tasks for non-trivial brief."""
        result = run_validate(self.root, "arch-team", "decompose")
        self.assertEqual(result.returncode, 0, result.stderr)

        plan_path = self.root / ".architect-dev-team" / "arch_team_plan.json"
        self.assertTrue(plan_path.exists())

        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        self.assertEqual(len(plan["research_tasks"]), 4)
        roles = {t["role"] for t in plan["research_tasks"]}
        self.assertEqual(roles, {"System Architecture", "Domain Intelligence", "Security / Trust", "Data / Interface"})

    def test_research_execution_creates_artifacts(self):
        """Research execution saves .md and .json results and updates plan status."""
        run_validate(self.root, "arch-team", "decompose")

        with runtime_fixture():
            for i in range(1, 5):
                task_id = f"research-{i:03d}"
                result = run_validate(self.root, "research", task_id, "execute")
                self.assertEqual(result.returncode, 0, f"Research {task_id} failed: {result.stderr}")

                md_path = self.root / ".architect-dev-team" / "research" / f"{task_id}.md"
                json_path = self.root / ".architect-dev-team" / "research" / f"{task_id}.json"
                self.assertTrue(md_path.exists(), f"Missing {md_path}")
                self.assertTrue(json_path.exists(), f"Missing {json_path}")

                # Verify plan updated
                plan_path = self.root / ".architect-dev-team" / "arch_team_plan.json"
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                task = next(t for t in plan["research_tasks"] if t["task_id"] == task_id)
                self.assertEqual(task["status"], "completed")
                self.assertIsNotNone(task.get("result_path"))

    def test_research_result_records_execution_mode(self):
        """A fixture research run is labelled as a fixture, never as native."""
        run_validate(self.root, "arch-team", "decompose")
        with runtime_fixture():
            run_validate(self.root, "research", "research-001", "execute")
        data = json.loads(
            (self.root / ".architect-dev-team" / "research" / "research-001.json")
            .read_text(encoding="utf-8"))
        self.assertEqual(data["execution_mode"], "fixture")
        self.assertEqual(data["agent"], "explore")
        self.assertTrue(data["session_id"])

    def test_integrate_research_into_architecture(self):
        """Integration produces architecture.md with research results."""
        run_validate(self.root, "arch-team", "decompose")
        with runtime_fixture():
            with runtime_fixture():
                for i in range(1, 5):
                    run_validate(self.root, "research", f"research-{i:03d}", "execute")

        result = run_validate(self.root, "arch-team", "integrate")
        self.assertEqual(result.returncode, 0, result.stderr)

        arch_path = self.root / ".architect-dev-team" / "architecture.md"
        self.assertTrue(arch_path.exists())
        content = arch_path.read_text(encoding="utf-8")
        self.assertIn("Research Results", content)
        self.assertIn("research-001", content)
        self.assertIn("research-002", content)
        # Fixture research is excluded from the architecture document and
        # reported separately, so it can never be presented as research.
        self.assertIn("__excluded_fixture__", content)
        self.assertNotIn("### research-001\n", content)


class TestTaskContracts(unittest.TestCase):
    """Test implementation and critic contract creation and validation."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self._init_git()

    def tearDown(self):
        self.temp.cleanup()

    def _init_git(self):
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.test"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.root, check=True)
        (self.root / "README.md").write_text("# Test\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=self.root, check=True)

    def test_create_implementation_contract(self):
        """Create implementation contract with all required fields."""
        result = run_validate(self.root, "task-contracts", "create-impl",
            "--task-id", "impl-001", "--role", "Backend Specialist",
            "--goal", "Implement API", "--arch-version", "v1",
            "--milestone", "M1", "--acceptance", "GET /api returns 200",
            "--required-checks", "unit-tests", "--model-profile", "medium")
        self.assertEqual(result.returncode, 0, result.stderr)

        contract_path = self.root / ".architect-dev-team" / "tasks" / "impl-001.json"
        self.assertTrue(contract_path.exists())

        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        self.assertEqual(contract["task_id"], "impl-001")
        self.assertEqual(contract["role"], "Backend Specialist")
        self.assertEqual(contract["goal"], "Implement API")
        self.assertEqual(contract["architecture_version"], "v1")
        self.assertEqual(contract["milestone_id"], "M1")
        self.assertIn("GET /api returns 200", contract["acceptance"])
        self.assertIn("unit-tests", contract["required_checks"])
        self.assertEqual(contract["model_profile"], "medium")
        self.assertEqual(contract["status"], "created")

    def test_create_critic_contract(self):
        """Create critic contract with independence tracking."""
        result = run_validate(self.root, "task-contracts", "create-critic",
            "--task-id", "critic-001", "--review-target", "impl-001",
            "--arch-version", "v1", "--milestone", "M1",
            "--model-profile", "medium")
        self.assertEqual(result.returncode, 0, result.stderr)

        contract_path = self.root / ".architect-dev-team" / "tasks" / "critic-001.json"
        self.assertTrue(contract_path.exists())

        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        self.assertEqual(contract["task_id"], "critic-001")
        self.assertEqual(contract["review_target"], "impl-001")
        # Independence is proven by runtime evidence, never declared up front.
        self.assertEqual(contract["independence"], "unavailable")
        self.assertEqual(contract["role"], "Independent Critic")
        self.assertIn("write:src/**", contract["prohibited_actions"])
        self.assertIn("file:line references", contract["evidence_requirements"])

    def test_contract_persistence_and_loading(self):
        """Contracts persist as JSON and Markdown and can be loaded."""
        run_validate(self.root, "task-contracts", "create-impl",
            "--task-id", "impl-001", "--role", "Backend",
            "--goal", "Test", "--arch-version", "v1", "--milestone", "M1")

        # Load via CLI list
        result = run_validate(self.root, "task-contracts", "list")
        self.assertEqual(result.returncode, 0)
        self.assertIn("impl-001", result.stdout)

        # Verify .md exists
        md_path = self.root / ".architect-dev-team" / "tasks" / "impl-001.md"
        self.assertTrue(md_path.exists())
        md_content = md_path.read_text(encoding="utf-8")
        self.assertIn("impl-001", md_content)


class TestProjectView(unittest.TestCase):
    """Test project overview generation and start gate."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self._init_git()
        run_validate(self.root, "intake")
        run_validate(self.root, "arch-team", "decompose")
        with runtime_fixture():
            with runtime_fixture():
                for i in range(1, 5):
                    run_validate(self.root, "research", f"research-{i:03d}", "execute")
        run_validate(self.root, "arch-team", "integrate")
        run_validate(self.root, "task-contracts", "create-impl",
            "--task-id", "impl-001", "--role", "Backend",
            "--goal", "Test", "--arch-version", "v1", "--milestone", "M1")
        run_validate(self.root, "task-contracts", "create-critic",
            "--task-id", "critic-001", "--review-target", "impl-001",
            "--arch-version", "v1", "--milestone", "M1")

    def tearDown(self):
        self.temp.cleanup()

    def _init_git(self):
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.test"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.root, check=True)
        (self.root / "README.md").write_text("# Test\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=self.root, check=True)

    def test_generate_project_view(self):
        """Project view generated with Mermaid diagram and start gate question."""
        result = run_validate(self.root, "project-view", "generate")
        self.assertEqual(result.returncode, 0, result.stderr)

        view_path = self.root / ".architect-dev-team" / "project_view.md"
        self.assertTrue(view_path.exists())
        content = view_path.read_text(encoding="utf-8")

        # Check structure
        self.assertIn("Project Overview:", content)
        self.assertIn("Component & Data Flow Diagram", content)
        self.assertIn("```mermaid", content)
        self.assertIn("graph TD", content)
        self.assertIn("Text Alternative", content)

        # Check start gate
        self.assertIn("Soll ich den ersten beschriebenen Meilenstein", content)
        self.assertIn("M1 starten", content)

        # Check roles and tasks
        self.assertIn("impl-001", content)
        self.assertIn("critic-001", content)
        self.assertIn("Backend Specialist", content)
        self.assertIn("Independent Critic", content)

        # Check mandatory checks section
        self.assertIn("Mandatory Checks", content)

    def test_project_view_status_tracking(self):
        """Project view status file created."""
        run_validate(self.root, "project-view", "generate")

        status_path = self.root / ".architect-dev-team" / "project_view_status.txt"
        self.assertTrue(status_path.exists())
        self.assertEqual(status_path.read_text(encoding="utf-8").strip(), "Entwurf")


class TestPairExecution(unittest.TestCase):
    """Test implementer/critic pair execution with repair loop."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self._init_git()
        run_validate(self.root, "task-contracts", "create-impl",
            "--task-id", "impl-001", "--role", "Backend",
            "--goal", "Test", "--arch-version", "v1", "--milestone", "M1")
        run_validate(self.root, "task-contracts", "create-critic",
            "--task-id", "critic-001", "--review-target", "impl-001",
            "--arch-version", "v1", "--milestone", "M1")

    def tearDown(self):
        self.temp.cleanup()

    def _init_git(self):
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.test"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.root, check=True)
        (self.root / "README.md").write_text("# Test\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=self.root, check=True)

    def test_pair_execution_refuses_a_fixture_review(self):
        """A fixture run is not a native review, so the pair refuses it."""
        with runtime_fixture():
            result = run_validate(self.root, "pair-exec", "run-pair",
                "--impl-task-id", "impl-001", "--critic-task-id", "critic-001")
        self.assertEqual(result.returncode, 5, result.stderr)
        self.assertIn("Running implementer: impl-001", result.stdout)
        self.assertIn("Running critic: critic-001", result.stdout)
        self.assertIn("critic report rejected", result.stdout)
        self.assertIn("native agent run", result.stdout)

        critic_path = self.root / ".architect-dev-team" / "tasks" / "critic-001.json"
        critic = json.loads(critic_path.read_text(encoding="utf-8"))
        self.assertEqual(critic["status"], "failed")
        # The implementer result is still recorded.
        impl = json.loads(
            (self.root / ".architect-dev-team" / "tasks" / "impl-001.json")
            .read_text(encoding="utf-8"))
        self.assertEqual(impl["status"], "completed")

    def test_pair_execution_records_distinct_sessions_and_rejects_fixture_independence(self):
        """Fixture runs are recorded honestly and never count as independent."""
        with runtime_fixture():
            result = run_validate(self.root, "pair-exec", "run-pair",
                "--impl-task-id", "impl-001", "--critic-task-id", "critic-001")
        self.assertEqual(result.returncode, 5, result.stderr)

        impl = json.loads((self.root / ".architect-dev-team" / "tasks" / "impl-001.json")
                          .read_text(encoding="utf-8"))
        critic = json.loads((self.root / ".architect-dev-team" / "tasks" / "critic-001.json")
                            .read_text(encoding="utf-8"))

        self.assertTrue(impl["session_id"])
        self.assertTrue(critic["session_id"])
        self.assertNotEqual(impl["session_id"], critic["session_id"])
        self.assertEqual(impl["execution_mode"], "fixture")
        self.assertEqual(critic["execution_mode"], "fixture")

        # The refusal names the fixture as the reason.
        self.assertIn("native agent run", critic["review_notes"])

    def test_repair_loop_is_not_entered_for_a_rejected_report(self):
        """A rejected report never reaches the repair loop."""
        with runtime_fixture():
            result = run_validate(self.root, "pair-exec", "run-pair",
                "--impl-task-id", "impl-001", "--critic-task-id", "critic-001",
                "--max-rounds", "2")
        self.assertEqual(result.returncode, 5)
        self.assertNotIn("Repair round", result.stdout)


class TestIntegration(unittest.TestCase):
    """Test final integration with test execution and report generation."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self._init_git()
        run_validate(self.root, "intake")
        run_validate(self.root, "arch-team", "decompose")
        with runtime_fixture():
            with runtime_fixture():
                for i in range(1, 5):
                    run_validate(self.root, "research", f"research-{i:03d}", "execute")
        run_validate(self.root, "arch-team", "integrate")
        run_validate(self.root, "task-contracts", "create-impl",
            "--task-id", "impl-001", "--role", "Backend",
            "--goal", "Test", "--arch-version", "v1", "--milestone", "M1",
            "--acceptance", "Test passes", "--required-checks", "unit-tests")
        run_validate(self.root, "task-contracts", "create-critic",
            "--task-id", "critic-001", "--review-target", "impl-001",
            "--arch-version", "v1", "--milestone", "M1")
        with runtime_fixture():
            run_validate(self.root, "pair-exec", "run-pair",
                "--impl-task-id", "impl-001", "--critic-task-id", "critic-001")

    def tearDown(self):
        self.temp.cleanup()

    def _init_git(self):
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.test"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.root, check=True)
        (self.root / "README.md").write_text("# Test\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=self.root, check=True)

    def test_integration_runs_tests_and_produces_report(self):
        """Integration runs pytest and generates report with independence evidence."""
        # Create tests directory and a passing test
        (self.root / "tests").mkdir(exist_ok=True)
        (self.root / "tests" / "test_sample.py").write_text(
            "def test_ok():\n    assert 1 + 1 == 2\n", encoding="utf-8")
        subprocess.run(["git", "add", "tests/test_sample.py"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "add test"], cwd=self.root, check=True)

        with runtime_fixture():
            result = run_validate(self.root, "integration", "run")

        report_path = self.root / ".architect-dev-team" / "integration_report.md"
        self.assertTrue(report_path.exists())
        content = report_path.read_text(encoding="utf-8")

        self.assertIn("Integration Report:", content)
        self.assertIn("impl-001", content)
        self.assertIn("critic-001", content)
        self.assertIn("PASS ", content)
        self.assertIn("Review Independence", content)
        # A fixture run must not be reported as an independent review.
        self.assertNotEqual(result.returncode, 0,
                            "fixture runs must not satisfy the integration gate")
        self.assertIn("not established", result.stdout)

    def test_integration_fails_on_test_failure(self):
        """Integration fails when mandatory checks fail."""
        # No tests = pytest fails
        result = run_validate(self.root, "integration", "run")
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL:", result.stdout)
        self.assertIn("WARNING: Some checks failed", result.stdout)

    def test_integration_runs_the_tests_of_the_fixture_project(self):
        """The default command must really execute the project test suite."""
        tests_dir = self.root / "tests"
        tests_dir.mkdir(exist_ok=True)
        (tests_dir / "test_fixture.py").write_text(
            "def test_fixture_ok():\n    assert 2 + 2 == 4\n", encoding="utf-8")
        subprocess.run(["git", "add", "tests/test_fixture.py"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture test"], cwd=self.root, check=True)
        with runtime_fixture():
            result = run_validate(self.root, "integration", "run")
        self.assertIn("PASS:", result.stdout, result.stderr)
        report = (self.root / ".architect-dev-team" / "integration_report.md").read_text(
            encoding="utf-8")
        self.assertIn("1 passed", report)

    def test_independence_evidence_recorded(self):
        """Critic independence tracked in integration report."""
        # Create tests directory and a passing test
        (self.root / "tests").mkdir(exist_ok=True)
        (self.root / "tests" / "test_ok.py").write_text(
            "def test_ok():\n    assert True\n", encoding="utf-8")
        subprocess.run(["git", "add", "tests/test_ok.py"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "add test"], cwd=self.root, check=True)

        with runtime_fixture():
            run_validate(self.root, "integration", "run")

        report_path = self.root / ".architect-dev-team" / "integration_report.md"
        content = report_path.read_text(encoding="utf-8")
        self.assertIn("Review Independence", content)
        self.assertIn("critic-001", content)


class TestStateCompatibility(unittest.TestCase):
    """Test that new state fields don't break existing validation."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self._init_git()

    def tearDown(self):
        self.temp.cleanup()

    def _init_git(self):
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.test"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.root, check=True)
        (self.root / "README.md").write_text("# Test\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=self.root, check=True)

    def test_new_state_fields_optional(self):
        """State validation works with new optional fields present."""
        state_path = self.root / ".architect-dev-team" / "state.json"
        state_path.parent.mkdir(exist_ok=True)

        state = {
            "schema_version": 2,
            "phase": "INTAKE",
            "approval_stage": None,
            "profile": "balanced",
            "architecture": None,
            "milestone": None,
            "approvals": [],
            "checks": [],
            "review": None,
            "completed": [],
            "open_issues": [],
            "constraints": [],
            "next_action": "Test",
            # New M2 fields
            "brief": None,
            "research_results": [],
            "task_contracts": [],
            "project_view": None,
            "pair_results": [],
            "lead_session": None,
            "arch_lead_session": None,
            "effort": {"tokens": 0, "time_seconds": 0, "agents": 0, "repair_rounds": 0}
        }
        state_path.write_text(json.dumps(state), encoding="utf-8")

        # Should not raise
        cmd = [PYTHON, str(VALIDATE_PY), "state", str(state_path), "--root", str(self.root)]
        result = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_new_fields_defaults_handled(self):
        """State without new fields still validates (backward compat)."""
        state_path = self.root / ".architect-dev-team" / "state.json"
        state_path.parent.mkdir(exist_ok=True)

        # Old state format without new fields
        state = {
            "schema_version": 2,
            "phase": "INTAKE",
            "approval_stage": None,
            "profile": "balanced",
            "architecture": None,
            "milestone": None,
            "approvals": [],
            "checks": [],
            "review": None,
            "completed": [],
            "open_issues": [],
            "constraints": [],
            "next_action": "Test",
        }
        state_path.write_text(json.dumps(state), encoding="utf-8")

        cmd = [PYTHON, str(VALIDATE_PY), "state", str(state_path), "--root", str(self.root)]
        result = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_architecture_approval_gate_still_works(self):
        """Architecture gate validates correctly with new fields."""
        state_path = self.root / ".architect-dev-team" / "state.json"
        state_path.parent.mkdir(exist_ok=True)

        # Create minimal architecture
        arch_path = self.root / ".architect-dev-team" / "architecture.md"
        arch_path.parent.mkdir(exist_ok=True)
        arch_bytes = ("# Architecture\n\n## Milestones\n\n| ID | Deliverable | Acceptance | "
                      "Required checks | Dependencies |\n| M1 | Test | OK | unit-tests | |\n"
                      ).encode("utf-8")
        arch_path.write_bytes(arch_bytes)
        arch_digest = hashlib.sha256(arch_bytes).hexdigest()

        state = {
            "schema_version": 2,
            "phase": "APPROVAL",
            "approval_stage": "architecture",
            "profile": "balanced",
            "architecture": {"path": ".architect-dev-team/architecture.md", "sha256": arch_digest},
            "milestone": {"id": "M1", "summary": "Test", "acceptance": ["OK"], "required_checks": ["unit-tests"]},
            "approvals": [],
            "checks": [{"name": "unit-tests", "required": True, "status": "not_run", "evidence": "", "waiver": None}],
            "review": None,
            "completed": [],
            "open_issues": [],
            "constraints": [],
            "next_action": "Implement",
        }
        # Bind the approval to the exact scope the gate computes.
        state["approvals"] = [{
            "kind": "architecture", "decision": "approved",
            "scope_sha256": v.scope(state), "review_sha256": None,
            "evidence": "test fixture approval for the exact scope",
            "recorded_at": "2026-10-20T12:00:00+00:00",
        }]
        state_path.write_text(json.dumps(state), encoding="utf-8")

        cmd = [PYTHON, str(VALIDATE_PY), "state", str(state_path), "--root", str(self.root), "--gate", "implement"]
        result = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)


class TestStartGateApproval(unittest.TestCase):
    """Test that start gate is distinct from architecture approval."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self._init_git()

    def tearDown(self):
        self.temp.cleanup()

    def _init_git(self):
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.test"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.root, check=True)
        (self.root / "README.md").write_text("# Test\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=self.root, check=True)

    def test_project_view_contains_explicit_start_question(self):
        """Project view contains the exact start gate question."""
        run_validate(self.root, "intake")
        run_validate(self.root, "arch-team", "decompose")
        with runtime_fixture():
            with runtime_fixture():
                for i in range(1, 5):
                    run_validate(self.root, "research", f"research-{i:03d}", "execute")
        run_validate(self.root, "arch-team", "integrate")
        run_validate(self.root, "task-contracts", "create-impl",
            "--task-id", "impl-001", "--role", "Backend",
            "--goal", "Test", "--arch-version", "v1", "--milestone", "M1")
        run_validate(self.root, "task-contracts", "create-critic",
            "--task-id", "critic-001", "--review-target", "impl-001",
            "--arch-version", "v1", "--milestone", "M1")

        run_validate(self.root, "project-view", "generate")

        view_path = self.root / ".architect-dev-team" / "project_view.md"
        content = view_path.read_text(encoding="utf-8")

        # Exact start gate question
        self.assertIn("Soll ich den ersten beschriebenen Meilenstein (M1) mit diesem Plan, Team, Skills und Prüfpolitik starten?", content)

        # Separate consent options
        self.assertIn("Skills/Installation separat freigeben", content)


if __name__ == "__main__":
    unittest.main()