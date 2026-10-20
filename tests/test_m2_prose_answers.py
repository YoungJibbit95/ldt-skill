"""A native agent that answers in prose still produces a structured result.

The runtime agents in this environment answer with prose and Markdown even
when the prompt asks for JSON. The core extracts the structure, records where
it came from, and applies the same validation: an extracted result that
states no acceptance and no evidence is not a success.
"""
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

from ldt_core import lead_execution as le  # noqa: E402
from ldt_core import pair_execution as pe  # noqa: E402
from ldt_core.agent_answers import (  # noqa: E402
    extract_lead_review, extract_specialist_result,
)
from ldt_core.runtime import AgentRun  # noqa: E402
from ldt_core.task_contracts import create_lead_contract  # noqa: E402

SPECIALIST_PROSE = """# Changes

- `src/registry.py`: canonicalise the address before the duplicate check
- `tests/test_registry.py`: added the case variant test

# Checks

- unit-tests: passed (13 passed)

# Summary

The store now compares the trimmed, lower-cased address, so a case variant is
rejected as a duplicate. All acceptance criteria are met.
"""

LEAD_PROSE = """# Assessment

- impl-001: the canonicalisation is implemented and the test passes

# Decisions

- impl-001: accepted. The acceptance criteria are met and the check passes.

# Summary

The deliverable satisfies the agreed acceptance criteria. The specialist is
accepted.
"""


class ProseSpecialist(unittest.TestCase):
    """A specialist that answered in prose."""

    def test_the_structure_is_extracted(self):
        result = extract_specialist_result(SPECIALIST_PROSE)
        self.assertEqual(result["extracted_from"], "markdown")
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["acceptance_met"])
        self.assertIn("src/registry.py", result["changes"])
        self.assertEqual(result["checks"][0]["name"], "unit-tests")
        self.assertEqual(result["checks"][0]["result"], "passed")
        self.assertIn("compares", result["summary"])

    def test_an_empty_answer_is_a_failure(self):
        result = extract_specialist_result("")
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["acceptance_met"])
        self.assertEqual(result["checks"], [])

    def test_a_prose_answer_is_not_a_claimed_success(self):
        """The core decides, not the extraction."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = create_lead_contract(
                task_id="lead-1", outcome="Deliver",
                architecture_path=".architect-dev-team/architecture.md",
                architecture_sha256="a" * 64, milestone_id="M1",
                base_revision="b" * 40, acceptance=["works"],
                required_checks=["unit-tests"],
                resource_budget={"tokens": 1000, "time_seconds": 60},
                max_specialists=3)
            roster = [{
                "task_id": "impl-001", "role": "Backend",
                "goal": "Implement it",
                "acceptance": ["returns 200"],
                "required_checks": ["unit-tests"],
                "file_ownership": {"src/api.py": "impl-001"},
                "model_profile": "medium", "review_assignment": "critic-001",
                "skill_pins": [],
            }]

            def fake_dispatch(prompt, role, cwd, **kwargs):
                if "plan" in kwargs.get("title", ""):
                    plan = {"validates_against_architecture": True,
                            "architecture_conflicts": [], "missing_information": [],
                            "risks": [], "assignments": roster,
                            "plan_summary": "One specialist."}
                    return AgentRun(status="completed", session_id="ses_plan",
                                    agent="plan", model="m", output=json.dumps(plan))
                if role == "Backend":
                    # The specialist answers in prose and names no check.
                    prose = SPECIALIST_PROSE.replace(
                        "- unit-tests: passed (13 passed)", "- the suite was run")
                    return AgentRun(status="completed", session_id="ses_spec",
                                    agent="general", model="m", output=prose)
                return AgentRun(status="completed", session_id="ses_review",
                                agent="general", model="m", output=LEAD_PROSE)

            with mock.patch.object(le, "dispatch", side_effect=fake_dispatch):
                result = le.run_department_lead(root, contract, roster, "# Arch")

            # The lead's answer said "accepted", but the core checks the
            # evidence the specialist reported.
            specialist = result.specialists[0]
            self.assertEqual(specialist["extracted_from"], "markdown")
            self.assertEqual(specialist["checks"], [])
            self.assertFalse(result.accepted,
                             "a specialist without a reported check is not accepted")


class ProseLeadReview(unittest.TestCase):
    """A lead that answered in prose."""

    def test_the_decision_is_extracted(self):
        review = extract_lead_review(LEAD_PROSE)
        self.assertEqual(review["extracted_from"], "markdown")
        self.assertTrue(review["accepted"])
        self.assertEqual(len(review["decisions"]), 1)
        self.assertEqual(review["decisions"][0]["task_id"], "impl-001")
        self.assertEqual(review["decisions"][0]["decision"], "accept")

    def test_a_rejection_is_extracted(self):
        prose = LEAD_PROSE.replace("accepted.", "rejected, the check did not run.")
        review = extract_lead_review(prose)
        self.assertFalse(review["accepted"])
        self.assertEqual(review["decisions"][0]["decision"], "reject")

    def test_a_prose_review_without_a_decision_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = create_lead_contract(
                task_id="lead-1", outcome="Deliver",
                architecture_path=".architect-dev-team/architecture.md",
                architecture_sha256="a" * 64, milestone_id="M1",
                base_revision="b" * 40, acceptance=["works"],
                required_checks=["unit-tests"],
                resource_budget={"tokens": 1000, "time_seconds": 60},
                max_specialists=3)
            roster = [{
                "task_id": "impl-001", "role": "Backend", "goal": "Implement it",
                "acceptance": ["returns 200"], "required_checks": ["unit-tests"],
                "file_ownership": {"src/api.py": "impl-001"},
                "model_profile": "medium", "review_assignment": "critic-001",
                "skill_pins": [],
            }]

            def fake_dispatch(prompt, role, cwd, **kwargs):
                if "plan" in kwargs.get("title", ""):
                    plan = {"validates_against_architecture": True,
                            "architecture_conflicts": [], "missing_information": [],
                            "risks": [], "assignments": roster,
                            "plan_summary": "One specialist."}
                    return AgentRun(status="completed", session_id="ses_plan",
                                    agent="plan", model="m", output=json.dumps(plan))
                if role == "Backend":
                    return AgentRun(status="completed", session_id="ses_spec",
                                    agent="general", model="m", output=SPECIALIST_PROSE)
                # Prose without a decision per specialist.
                return AgentRun(status="completed", session_id="ses_review",
                                agent="general", model="m",
                                output="# Summary\nEverything looks fine to me.")

            with mock.patch.object(le, "dispatch", side_effect=fake_dispatch):
                result = le.run_department_lead(root, contract, roster, "# Arch")

            self.assertEqual(result.status, "failed")
            self.assertTrue(any("JSON" in u for u in result.unresolved))


class PairProseImplementer(unittest.TestCase):
    """The pair path reads a prose answer of the implementer."""

    def test_the_raw_output_stays_in_the_evidence(self):
        run = AgentRun(status="completed", session_id="ses_impl", agent="general",
                       model="m", output=SPECIALIST_PROSE,
                       evidence={"execution_mode": "native"})
        data = pe._parse_agent_output(run)
        self.assertEqual(data["extracted_from"], "markdown")
        self.assertIn("raw_output", data["evidence"])
        self.assertIn("src/registry.py", data["changes"])


if __name__ == "__main__":
    unittest.main()
