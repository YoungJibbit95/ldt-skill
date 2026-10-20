"""The round 4 defects, each with a regression.

The independent review of the fourth round found these. Every one of them
failed against the reviewed state and passes now.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / ".agents/skills/architect-dev-team/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from ldt_core import critic_report as cr  # noqa: E402
from ldt_core import lead_execution as le  # noqa: E402
from ldt_core import pair_execution as pe  # noqa: E402
from ldt_core.agent_answers import extract_lead_review  # noqa: E402
from ldt_core.document_reader import strip_json_objects  # noqa: E402
from ldt_core.runtime import AgentRun  # noqa: E402
from ldt_core.task_contracts import (  # noqa: E402
    create_critic_contract, create_implementation_contract, create_lead_contract,
    save_contract,
)

VERIFIED = {"verified": True, "agent": "explore", "read_only_agent": True}


def json_report(revision, recommendation="approve", findings=None, task_id="critic-001"):
    return {
        "task_id": task_id, "reviewed_task_id": "impl-001",
        "reviewed_revision": revision,
        "reviewer": {"session_id": "ses_critic", "agent": "explore", "model": "m",
                     "execution_mode": "native", "verified": True,
                     "read_only_agent": True},
        "coverage": {"requirements_checked": ["register rejects a duplicate address"],
                     "files_inspected": ["src/registry.py"],
                     "interfaces_checked": [], "evidence_references": [],
                     "checks_run": [{"name": "unit-tests", "result": "passed",
                                     "evidence": "13 passed"}],
                     "unverified_areas": []},
        "findings": findings or [], "verified_non_findings": ["looks right"],
        "confidence": "high", "limitations": [],
        "recommendation": recommendation, "summary": "Reviewed.",
    }


PROSE_BLOCKER = """
# Review Assignment: critic-001

## Assignment Overview

**Required check:** unit-tests

## Findings

- blocker src/registry.py:12 the duplicate check is case-sensitive
"""


class PairFixture(unittest.TestCase):
    """A pair with an implementer and a critic."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        impl = create_implementation_contract(
            task_id="impl-001", role="Backend Specialist", goal="Implement",
            architecture_version="v1", milestone_id="M1", base_revision="a" * 40,
            acceptance=["register rejects a duplicate address"],
            required_checks=["unit-tests"],
            resource_budget={"tokens": 1000, "time_seconds": 60},
            review_assignment="critic-001")
        critic = create_critic_contract(
            task_id="critic-001", review_target="impl-001",
            architecture_version="v1", milestone_id="M1", base_revision="a" * 40,
            requirements=["register rejects a duplicate address"],
            files_in_scope=["src/registry.py"],
            required_checks=["unit-tests"],
            resource_budget={"tokens": 1000, "time_seconds": 60})
        save_contract(impl, self.root)
        save_contract(critic, self.root)
        self.revision = pe._current_revision(self.root)

    def _impl(self):
        return AgentRun(status="completed", session_id="ses_impl", agent="general",
                        model="m", output="{}",
                        evidence={"execution_mode": "native"})

    def _critic(self, output, session="ses_critic"):
        return AgentRun(status="completed", session_id=session, agent="explore",
                        model="m", output=output,
                        evidence={"execution_mode": "native"})

    def _repair(self):
        return AgentRun(status="completed", session_id="ses_repair", agent="general",
                        model="m", output="{}",
                        evidence={"execution_mode": "native"})


class RepairLoopCanSucceed(PairFixture):
    """The re-review is asked for the revision that exists after the repair."""

    def test_the_re_review_is_prompted_with_the_revision(self):
        asked = {}

        def fake_run_critic(root, contract, implementer_result, **kwargs):
            asked["revision"] = kwargs.get("revision")
            return self._critic(json.dumps(json_report(kwargs.get("revision", ""))))

        finding = [{"severity": "major", "file": "src/registry.py", "line": 12,
                    "issue": "case sensitive", "reproduction": "x",
                    "reference": "y"}]
        with mock.patch.object(pe, "run_implementer", return_value=self._impl()), \
             mock.patch.object(pe, "run_critic", side_effect=fake_run_critic), \
             mock.patch.object(pe, "dispatch_subagent", return_value=self._repair()), \
             mock.patch.object(pe, "verify_session", return_value=VERIFIED):
            code = pe.pair_execution_cli(
                self.root, "run-pair", impl_task_id="impl-001",
                critic_task_id="critic-001", max_rounds=2)
        self.assertEqual(code, 0,
                         "a repair that is verified must not fail the pair")
        self.assertTrue(asked.get("revision"),
                        "the re-review has to be asked for a revision")

    def test_the_prose_path_does_not_rescue_a_refused_report(self):
        """A JSON report that names a stale revision stays refused."""
        stale = json_report("STALE-REVISION")
        answer = json.dumps(stale) + "\n\n" + PROSE_BLOCKER
        with mock.patch.object(pe, "verify_session", return_value=VERIFIED):
            report, errors = pe._critic_report_from_run(
                self.root, self._critic(answer),
                load_critic(self.root), self._impl(), self.revision)
        self.assertTrue(errors, "a stale report must stay refused")
        self.assertIsNone(report)

    def test_a_prose_blocker_refuses_a_json_approval(self):
        answer = json.dumps(json_report(self.revision, "approve")) + "\n\n" + PROSE_BLOCKER
        with mock.patch.object(pe, "verify_session", return_value=VERIFIED):
            report, errors = pe._critic_report_from_run(
                self.root, self._critic(answer),
                load_critic(self.root), self._impl(), self.revision)
        self.assertTrue(errors,
                        "a blocker in the review text must refuse the approval")
        self.assertIsNone(report)

    def test_a_prose_blocker_never_leaves_the_pair_with_exit_zero(self):
        def fake_run_critic(root, contract, implementer_result, **kwargs):
            return self._critic(PROSE_BLOCKER)

        with mock.patch.object(pe, "run_implementer", return_value=self._impl()), \
             mock.patch.object(pe, "run_critic", side_effect=fake_run_critic), \
             mock.patch.object(pe, "dispatch_subagent", return_value=self._repair()), \
             mock.patch.object(pe, "verify_session", return_value=VERIFIED):
            code = pe.pair_execution_cli(
                self.root, "run-pair", impl_task_id="impl-001",
                critic_task_id="critic-001", max_rounds=2)
        self.assertNotEqual(code, 0)


def load_critic(root):
    from ldt_core.task_contracts import load_contract
    return load_contract(root, "critic-001")


class ShippedStateTemplateIsValid(unittest.TestCase):
    """The template a project is bootstrapped from has to validate."""

    def test_the_shipped_template_validates(self):
        from ldt_core.state import state as validate_state
        template = (REPO / ".agents/skills/architect-dev-team/assets"
                    / "state.template.json")
        value = json.loads(template.read_text(encoding="utf-8"))
        validate_state(value, REPO)
        self.assertIn("approved_skills", value,
                      "the template has to carry the approved skills")


class ExtractionHonestyRound4(unittest.TestCase):
    """The reader does not take a result from another check."""

    VERDICT = "**Overall verdict**: PASS - no blocking defects found\n\n"

    def test_a_count_of_another_check_is_not_used(self):
        report = cr.parse_critic_report_markdown(
            self.VERDICT + "## Checks\n\n| other-tests | 13 passed |\n",
            requirements=[], required_checks=["unit-tests"])
        self.assertEqual(report.coverage.checks_run[0]["result"], "not_run")

    def test_a_check_that_did_not_run_is_not_a_pass(self):
        report = cr.parse_critic_report_markdown(
            self.VERDICT + "| unit-tests | not run, no failures to report |",
            requirements=[], required_checks=["unit-tests"])
        self.assertEqual(report.coverage.checks_run[0]["result"], "not_run")

    def test_the_section_gives_the_finding_its_severity(self):
        prose = (self.VERDICT + "## Defects\n\n"
                 "- `register()` accepts a case variant\n")
        report = cr.parse_critic_report_markdown(prose, requirements=[],
                                                 required_checks=[])
        self.assertTrue(report.findings)
        self.assertEqual(report.findings[0].severity, "major")

    def test_a_risk_section_gives_an_observation(self):
        prose = (self.VERDICT + "## Risks Identified\n\n"
                 "- `REGISTRY` is publicly mutable\n")
        report = cr.parse_critic_report_markdown(prose, requirements=[],
                                                 required_checks=[])
        self.assertTrue(report.findings)
        self.assertEqual(report.findings[0].severity, "info")

    def test_approve_with_findings_is_honoured(self):
        prose = ("**Overall verdict**: approve with findings\n\n"
                 "## Findings\n\n- major src/a.py:1 the check is weak\n")
        report = cr.parse_critic_report_markdown(prose, requirements=[],
                                                 required_checks=[])
        self.assertIsNotNone(report)
        self.assertEqual(report.recommendation, "approve_with_findings")


class StripperSurvivesAnUnbalancedBrace(unittest.TestCase):
    """The JSON is removed even when an unbalanced brace precedes it."""

    def test_the_json_is_removed(self):
        text = "Unbalanced { brace first.\n" + json.dumps(json_report("rev"))
        stripped = strip_json_objects(text)
        self.assertNotIn('"reviewed_revision"', stripped)


class LeadDoesNotFabricateAnAcceptance(unittest.TestCase):
    """The core does not guess which specialist the lead accepted."""

    def test_an_unknown_specialist_is_not_a_decision(self):
        prose = ("# Verdict: PASS\n\n# Decisions\n\n"
                 "- impl-999: rejected, the check did not run\n")
        review = extract_lead_review(prose, ["impl-001"])
        self.assertEqual(review["decisions"], [])
        self.assertFalse(review["accepted"])

    def test_one_specialist_may_be_inferred_from_the_verdict(self):
        prose = "# Verdict: completed\n\nThe work is delivered.\n"
        review = extract_lead_review(prose, ["impl-001"])
        self.assertEqual(len(review["decisions"]), 1)
        self.assertEqual(review["decisions"][0]["decision"], "accept")


class SpecialistContractIsNotAFrameViolation(unittest.TestCase):
    """Filling in the task contract is part of the specialist's task."""

    def test_the_contract_file_is_not_a_violation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "api.py").write_text("# owned\n", encoding="utf-8")
            contract = create_implementation_contract(
                task_id="impl-001", role="Backend Specialist", goal="Implement",
                architecture_version="v1", milestone_id="M1", base_revision="a" * 40,
                acceptance=["works"], required_checks=["unit-tests"],
                resource_budget={"tokens": 1000, "time_seconds": 60},
                file_ownership={"src/api.py": "impl-001"})
            save_contract(contract, root)

            def fake_dispatch(prompt, role, cwd, **kwargs):
                # The specialist fills in its own contract.
                tasks = root / ".architect-dev-team" / "tasks"
                tasks.mkdir(parents=True, exist_ok=True)
                (tasks / "impl-001.json").write_text(json.dumps({
                    "task_id": "impl-001", "status": "completed",
                    "changes": ["src/api.py"], "acceptance_met": True,
                    "evidence": {"unit-tests": "13 passed"},
                    "checks": [{"name": "unit-tests", "result": "passed",
                                "evidence": "13 passed"}],
                }), encoding="utf-8")
                return AgentRun(status="completed", session_id="ses_spec",
                                agent="general", model="m", output="{}")

            with mock.patch.object(le, "dispatch", side_effect=fake_dispatch):
                result = le._run_specialist(root, contract)

            self.assertEqual(result.get("frame_violations"), [])
            self.assertEqual(result.get("result_source"), "task_contract")
            self.assertEqual(result.get("status"), "completed")


class ApprovedSkillsAreEffective(unittest.TestCase):
    """A skill the project approved may be pinned."""

    def test_the_contract_validator_reads_the_approved_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".architect-dev-team").mkdir()
            (root / ".architect-dev-team" / "state.json").write_text(json.dumps({
                "schema_version": 2, "phase": "INTAKE", "approval_stage": None,
                "profile": "balanced", "architecture": None, "milestone": None,
                "milestone": {"id": "M1", "summary": "Work.",
                              "acceptance": ["works"],
                              "required_checks": ["unit-tests"]},
                "approvals": [], "checks": [], "review": None, "completed": [],
                "open_issues": [], "constraints": [],
                "next_action": "Do something.", "approved_skills": ["approved-skill"],
            }), encoding="utf-8")
            contract = create_implementation_contract(
                task_id="impl-001", role="Backend Specialist", goal="Implement",
                architecture_version="v1", milestone_id="M1", base_revision="a" * 40,
                acceptance=["works"], required_checks=["unit-tests"],
                resource_budget={"tokens": 1000, "time_seconds": 60},
                skill_pins=["approved-skill@1.0.0"])
            save_contract(contract, root)
            result = subprocess.run(
                [sys.executable, "-B", str(SCRIPTS / "validate.py"),
                 "task-contracts", str(root), "validate", "--task-id", "impl-001"],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(result.returncode, 0,
                         f"an approved skill must be accepted: {result.stdout}"
                         f"{result.stderr}")


if __name__ == "__main__":
    unittest.main()
