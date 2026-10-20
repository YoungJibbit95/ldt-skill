"""The lead's write frame is enforced, not just stated."""
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
from ldt_core.runtime import AgentRun  # noqa: E402
from ldt_core.task_contracts import create_lead_contract  # noqa: E402


class LeadWriteFrame(unittest.TestCase):
    """The lead may merge, but only inside its frame."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        (self.root / "src").mkdir()
        (self.root / "src" / "api.py").write_text("# owned\n", encoding="utf-8")
        (self.root / "outside.py").write_text("# not owned\n", encoding="utf-8")
        self.contract = create_lead_contract(
            task_id="lead-1", outcome="Deliver",
            architecture_path=".architect-dev-team/architecture.md",
            architecture_sha256="a" * 64, milestone_id="M1", base_revision="b" * 40,
            acceptance=["works"], required_checks=["unit-tests"],
            resource_budget={"tokens": 1000, "time_seconds": 60},
            max_specialists=3)
        self.roster = [{"task_id": "impl-001",
                        "file_ownership": {"src/api.py": "impl-001"}}]

    def _plan(self):
        return json.dumps({
            "validates_against_architecture": True,
            "architecture_conflicts": [], "missing_information": [], "risks": [],
            "assignments": [{
                "task_id": "impl-001", "role": "Backend", "goal": "Implement it",
                "file_ownership": {"src/api.py": "impl-001"},
                "acceptance": ["returns 200"], "required_checks": ["unit-tests"],
                "model_profile": "medium", "review_assignment": "critic-001",
                "skill_pins": [],
            }],
            "plan_summary": "One specialist.",
        })

    def _review(self):
        return json.dumps({
            "accepted": True,
            "decisions": [{"task_id": "impl-001", "decision": "accept",
                            "reason": "ok", "correction": {"goal": "", "checks": []}}],
            "unresolved": [], "escalated": False, "summary": "Accepted.",
        })

    def _dispatch(self, mutate=None):
        def fake_dispatch(prompt, role, cwd, **kwargs):
            if "plan" in kwargs.get("title", ""):
                return AgentRun(status="completed", session_id="ses_plan",
                                agent="plan", model="m", output=self._plan())
            if role == "Backend":
                return AgentRun(status="completed", session_id="ses_spec",
                                agent="general", model="m",
                                output=json.dumps({"status": "completed", "changes": [],
                                                   "acceptance_met": True, "findings": [],
                                                   "evidence": {"unit-tests": "1 passed"},
                                                   "checks": [{"name": "unit-tests",
                                                               "result": "passed",
                                                               "evidence": "1 passed"}],
                                                   "risks": [], "unresolved": [],
                                                   "summary": "done"}))
            if mutate:
                mutate()
            return AgentRun(status="completed", session_id="ses_review",
                            agent="general", model="m", output=self._review())
        return fake_dispatch

    def test_a_change_inside_the_frame_is_allowed(self):
        def mutate():
            (self.root / "src" / "api.py").write_text("# merged\n", encoding="utf-8")
        with mock.patch.object(le, "dispatch", side_effect=self._dispatch(mutate)):
            result = le.run_department_lead(self.root, self.contract, self.roster, "# Arch")
        self.assertNotIn("write_frame_violated",
                         [t.get("outcome") for t in result.evidence.get("trail", [])])
        self.assertFalse(result.escalated)

    def test_a_change_outside_the_frame_is_refused(self):
        def mutate():
            (self.root / "outside.py").write_text("# touched\n", encoding="utf-8")
        with mock.patch.object(le, "dispatch", side_effect=self._dispatch(mutate)):
            result = le.run_department_lead(self.root, self.contract, self.roster, "# Arch")
        self.assertTrue(result.escalated)
        self.assertEqual(result.status, "escalated")
        self.assertTrue(any("outside its write frame" in u for u in result.unresolved))

    def test_the_plan_phase_uses_the_read_only_agent(self):
        agents = []

        def fake_dispatch(prompt, role, cwd, **kwargs):
            agents.append((kwargs.get("title", ""), kwargs.get("agent")))
            if "plan" in kwargs.get("title", ""):
                return AgentRun(status="completed", session_id="ses_plan",
                                agent="plan", model="m", output=self._plan())
            if role == "Backend":
                return AgentRun(status="completed", session_id="ses_spec",
                                agent="general", model="m",
                                output=json.dumps({"status": "completed", "changes": [],
                                                   "acceptance_met": True, "findings": [],
                                                   "evidence": {"unit-tests": "1 passed"},
                                                   "checks": [{"name": "unit-tests",
                                                               "result": "passed",
                                                               "evidence": "1 passed"}],
                                                   "risks": [], "unresolved": [],
                                                   "summary": "done"}))
            return AgentRun(status="completed", session_id="ses_review",
                            agent="general", model="m", output=self._review())

        with mock.patch.object(le, "dispatch", side_effect=fake_dispatch):
            le.run_department_lead(self.root, self.contract, self.roster, "# Arch")

        plan_agents = [agent for title, agent in agents if "plan" in title]
        review_agents = [agent for title, agent in agents if "review" in title]
        self.assertTrue(plan_agents)
        self.assertTrue(review_agents)
        # The plan phase may not write; the merge phase may.
        self.assertEqual(plan_agents[0], "plan")
        self.assertNotEqual(review_agents[0], "plan")


if __name__ == "__main__":
    unittest.main()
