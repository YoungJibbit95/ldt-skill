"""A reviewer that answers in prose still produces a validated report."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / ".agents/skills/architect-dev-team/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from ldt_core import critic_report as cr  # noqa: E402
from ldt_core import pair_execution as pe  # noqa: E402
from ldt_core.runtime import AgentRun  # noqa: E402
from ldt_core.task_contracts import create_critic_contract  # noqa: E402

PROSE = """# Critic Report: impl-001

**Overall verdict**: PASS - no blocking defects found

## 1. Requirements Verification

| Requirement | Status | Evidence |
|---|---|---|
| register rejects a duplicate address | **PASS** | src/registry.py:53-54 |
| register rejects a case variant | **PASS** | tests/test_registry.py:20 |

## 2. Checks

| unit-tests | passed | 10 passed |

Confidence: high
"""


class ProseReview(unittest.TestCase):
    """A Markdown review is extracted, bound and validated."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.critic = create_critic_contract(
            task_id="critic-001", review_target="impl-001",
            architecture_version="v1", milestone_id="M1", base_revision="a" * 40,
            requirements=["register rejects a duplicate address",
                          "register rejects a case variant"],
            files_in_scope=["src/registry.py", "tests/test_registry.py"],
            required_checks=["unit-tests"],
            resource_budget={"tokens": 1000, "time_seconds": 60})
        self.verified = {"verified": True, "agent": "explore", "read_only_agent": True}

    def _run(self, output):
        return AgentRun(status="completed", session_id="ses_critic", agent="explore",
                        model="m", output=output,
                        evidence={"execution_mode": "native"})

    def _impl(self):
        return AgentRun(status="completed", session_id="ses_impl", agent="general",
                        model="m", output="{}", evidence={"execution_mode": "native"})

    def test_a_prose_review_becomes_a_validated_report(self):
        revision = pe._current_revision(self.root)
        with mock.patch.object(pe, "verify_session", return_value=self.verified):
            report, errors = pe._critic_report_from_run(
                self.root, self._run(PROSE), self.critic, self._impl(), revision)
        self.assertEqual(errors, [])
        self.assertIsNotNone(report)
        self.assertEqual(report.task_id, "critic-001")
        self.assertEqual(report.reviewed_task_id, "impl-001")
        self.assertEqual(report.reviewed_revision, revision)
        self.assertEqual(report.reviewer.session_id, "ses_critic")
        self.assertTrue(report.reviewer.read_only_agent)
        self.assertEqual(report.confidence, "high")
        self.assertEqual(report.recommendation, "approve")
        self.assertEqual(report.coverage.requirements_checked,
                         ["register rejects a duplicate address",
                          "register rejects a case variant"])
        self.assertIn("src/registry.py", report.coverage.files_inspected)
        self.assertEqual(report.coverage.checks_run[0]["name"], "unit-tests")
        self.assertEqual(report.coverage.checks_run[0]["result"], "passed")

    def test_a_prose_review_that_omits_a_check_is_refused(self):
        revision = pe._current_revision(self.root)
        critic = create_critic_contract(
            task_id="critic-001", review_target="impl-001",
            architecture_version="v1", milestone_id="M1", base_revision="a" * 40,
            requirements=["register rejects a duplicate address"],
            files_in_scope=["src/registry.py"],
            required_checks=["unit-tests", "contract-test"],
            resource_budget={"tokens": 1000, "time_seconds": 60})
        with mock.patch.object(pe, "verify_session", return_value=self.verified):
            report, errors = pe._critic_report_from_run(
                self.root, self._run(PROSE), critic, self._impl(), revision)
        self.assertTrue(errors)
        self.assertTrue(any("contract-test" in e for e in errors))

    def test_a_prose_review_with_a_blocking_finding_is_refused(self):
        revision = pe._current_revision(self.root)
        prose = PROSE.replace(
            "**Overall verdict**: PASS - no blocking defects found",
            "**Overall verdict**: FAIL - a blocking defect was found")
        with mock.patch.object(pe, "verify_session", return_value=self.verified):
            report, errors = pe._critic_report_from_run(
                self.root, self._run(prose), self.critic, self._impl(), revision)
        self.assertTrue(errors, "a failing verdict must not produce an accepted report")
        self.assertIsNone(report,
                          "a failing verdict must not produce a report at all")

    def test_a_prose_review_with_a_readable_blocker_is_refused(self):
        """A blocker the core can read out is never a clean review."""
        revision = pe._current_revision(self.root)
        prose = PROSE + (
            "\n\n## Findings\n\n"
            "- blocker src/registry.py:12 the duplicate check is case-sensitive\n")
        with mock.patch.object(pe, "verify_session", return_value=self.verified):
            report, errors = pe._critic_report_from_run(
                self.root, self._run(prose), self.critic, self._impl(), revision)
        self.assertTrue(errors)
        self.assertIsNone(report)

    def test_a_defect_the_core_cannot_read_out_is_refused(self):
        """A remark the core does not understand is not a clean review."""
        revision = pe._current_revision(self.root)
        prose = PROSE + (
            "\n\nThe duplicate check is case-sensitive, so it accepts "
            "A@x and a@x. This is a blocker.\n")
        with mock.patch.object(pe, "verify_session", return_value=self.verified):
            report, errors = pe._critic_report_from_run(
                self.root, self._run(prose), self.critic, self._impl(), revision)
        self.assertTrue(errors,
                        "a defect the core cannot read out must not be accepted")
        self.assertIsNone(report)

    def test_the_extraction_keeps_the_contract_as_the_authority(self):
        report = cr.parse_critic_report_markdown(
            PROSE,
            requirements=["register rejects a duplicate address",
                          "register rejects a case variant"],
            required_checks=["unit-tests"])
        self.assertEqual(len(report.coverage.requirements_checked), 2)
        self.assertEqual(len(report.coverage.checks_run), 1)
        self.assertTrue(report.coverage.files_inspected)


if __name__ == "__main__":
    unittest.main()
