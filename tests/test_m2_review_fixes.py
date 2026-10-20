"""Regression tests for the defects found by the independent M2 Slice 1 review.

Every test here fails against the state that was reviewed and passes only
with the repaired behaviour.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / ".agents/skills/architect-dev-team/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from ldt_core import runtime as rt  # noqa: E402
from ldt_core import task_contracts as tc  # noqa: E402
from ldt_core.common import Invalid  # noqa: E402
from ldt_core.task_contracts import CriticContract, TaskContract  # noqa: E402


class FailedRunIsNotAReview(unittest.TestCase):
    """A run that did not complete is not a review."""

    def _run(self, session, agent, status):
        return rt.AgentRun(status=status, session_id=session, agent=agent, model="m",
                           evidence={"execution_mode": "native"})

    def test_failed_critic_is_not_independent(self):
        with mock.patch.object(rt, "verify_session",
                               return_value={"verified": True, "agent": "explore",
                                             "read_only_agent": True}):
            report = rt.independence_report(
                self._run("ses_i", "general", "completed"),
                self._run("ses_c", "explore", "failed"))
        self.assertEqual(report["independence"], "unavailable")
        self.assertTrue(any("did not complete" in r for r in report["reasons"]))

    def test_failed_implementer_is_not_independent(self):
        with mock.patch.object(rt, "verify_session",
                               return_value={"verified": True, "agent": "explore",
                                             "read_only_agent": True}):
            report = rt.independence_report(
                self._run("ses_i", "general", "failed"),
                self._run("ses_c", "explore", "completed"))
        self.assertEqual(report["independence"], "unavailable")
        self.assertTrue(any("did not complete" in r for r in report["reasons"]))


class RuntimeVerifiedAgentIsAuthoritative(unittest.TestCase):
    """The reviewer agent is the one the runtime recorded."""

    def test_requested_read_only_but_ran_writable_is_rejected(self):
        implementer = rt.AgentRun(status="completed", session_id="ses_i", agent="general",
                                  model="m", evidence={"execution_mode": "native"})
        critic = rt.AgentRun(status="completed", session_id="ses_c", agent="explore",
                             model="m", evidence={"execution_mode": "native"})
        with mock.patch.object(rt, "verify_session", side_effect=lambda sid, cwd=None: {
            "verified": True,
            "agent": "general" if sid == "ses_i" else "build",
            "read_only_agent": False,
        }), mock.patch.object(rt, "is_read_only_agent", return_value=False):
            report = rt.independence_report(implementer, critic)
        self.assertEqual(report["independence"], "unavailable")
        self.assertTrue(any("not read-only" in r for r in report["reasons"]))


class ReadOnlyAgentIsVerifiedNotAssumed(unittest.TestCase):
    """The read-only property comes from the runtime, not a constant."""

    def test_read_only_agents_are_derived_from_permissions(self):
        details = {
            "explore": {"mode": "subagent", "permissions": [
                {"action": "*", "resource": "*", "effect": "allow"},
                {"action": "*", "resource": "*", "effect": "deny"},
                {"action": "shell", "resource": "*", "effect": "allow"},
                {"action": "read", "resource": "*", "effect": "allow"},
            ]},
            "general": {"mode": "subagent", "permissions": [
                {"action": "*", "resource": "*", "effect": "allow"},
            ]},
        }
        with mock.patch.object(rt, "agent_permissions", return_value=details):
            read_only = rt.read_only_agents()
        self.assertIn("explore", read_only)
        self.assertNotIn("general", read_only)

    def test_unqueryable_runtime_does_not_grant_a_write_boundary(self):
        with mock.patch.object(rt, "agent_permissions", return_value={}):
            self.assertFalse(rt.is_read_only_agent("general"))
            # Not even the agent that is read-only in the real runtime: an
            # unverified agent must never be treated as a write boundary.
            self.assertFalse(rt.is_read_only_agent("explore"))
            self.assertFalse(rt.is_read_only_agent("plan"))


class RoleMappingIsExact(unittest.TestCase):
    """A role must not be routed to a read-only agent by a substring match."""

    def test_substring_roles_do_not_change_the_agent(self):
        # A planning-sounding implementer role must stay writable.
        self.assertEqual(rt.agent_for_role("Planar Specialist"), "general")
        self.assertEqual(rt.agent_for_role("Implementation Planner"), "general")
        # A reviewer role is correctly read-only.
        self.assertEqual(rt.agent_for_role("Code Reviewer"), "explore")

    def test_explicit_roles_map_correctly(self):
        self.assertEqual(rt.agent_for_role("Independent Critic"), "explore")
        self.assertEqual(rt.agent_for_role("Backend Specialist"), "general")
        self.assertEqual(rt.agent_for_role("research"), "explore")
        self.assertEqual(rt.agent_for_role("Architecture Lead"), "plan")


class TaskIdSafety(unittest.TestCase):
    """A task id becomes a file name and must stay inside the task folder."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def test_traversal_task_id_is_rejected(self):
        for bad in ("../../../evil", "..\\..\\evil", "a/b", "a:b", ".hidden", "", ".."):
            with self.subTest(task_id=bad):
                with self.assertRaises(Invalid):
                    tc.safe_task_id(bad)

    def test_normal_task_id_is_accepted(self):
        self.assertEqual(tc.safe_task_id("impl-001"), "impl-001")
        self.assertEqual(tc.safe_task_id("critic-42"), "critic-42")

    def test_saving_a_traversal_task_id_writes_nowhere(self):
        contract = TaskContract(task_id="../../../evil", role="Backend", goal="g",
                                architecture_version="v1", milestone_id="M1",
                                base_revision="a" * 40)
        with self.assertRaises(Invalid):
            tc.save_contract(contract, self.root)
        self.assertFalse((self.root.parent / "evil.json").exists())


class CriticContractDoesNotPreclaimIndependence(unittest.TestCase):
    """A critic contract must not carry an independence claim up front."""

    def test_new_critic_contract_is_not_declared_independent(self):
        contract = CriticContract(task_id="critic-001", review_target="impl-001",
                                  architecture_version="v1", milestone_id="M1",
                                  base_revision="a" * 40)
        self.assertEqual(contract.independence, "unavailable")


class StartGateBindsToRealContracts(unittest.TestCase):
    """The start gate must not be bypassable by an empty state list."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.state_dir = self.root / ".architect-dev-team"
        self.state_dir.mkdir()
        self.addCleanup(self.temp.cleanup)

    def _state(self, **overrides):
        import hashlib
        arch = self.state_dir / "architecture.md"
        arch.write_text("# Architecture\n\n## Milestones\n", encoding="utf-8")
        digest = hashlib.sha256(arch.read_bytes()).hexdigest()
        data = {
            "schema_version": 2, "phase": "IMPLEMENTATION", "approval_stage": None,
            "profile": "balanced",
            "architecture": {"path": ".architect-dev-team/architecture.md", "sha256": digest},
            "milestone": {"id": "M1", "summary": "s", "acceptance": ["a"],
                          "required_checks": ["unit-tests"]},
            "approvals": [], "checks": [
                {"name": "unit-tests", "required": True, "status": "not_run",
                 "evidence": "", "waiver": None}],
            "review": None, "completed": [],
            "open_issues": [], "constraints": [], "next_action": "Implement",
            "task_contracts": [],
        }
        data.update(overrides)
        from ldt_core.approvals import scope
        data["approvals"] = [{
            "kind": "architecture", "decision": "approved",
            "scope_sha256": scope(data), "review_sha256": None,
            "evidence": "test fixture approval",
            "recorded_at": "2026-10-20T12:00:00+00:00",
        }]
        return data

    def test_contracts_on_disk_require_a_start_approval(self):
        from ldt_core.state import state as validate_state
        tasks = self.state_dir / "tasks"
        tasks.mkdir()
        (tasks / "impl-001.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(Invalid, "missing start approval"):
            validate_state(self._state(), self.root, "implement")

    def test_without_contracts_the_legacy_path_is_unchanged(self):
        from ldt_core.state import state as validate_state
        validate_state(self._state(), self.root, "implement")

    def test_creating_a_contract_records_it_in_the_state(self):
        state_path = self.state_dir / "state.json"
        state_path.write_text(json.dumps(self._state(phase="INTAKE")), encoding="utf-8")
        tc.record_contract_in_state(self.root, "impl-001")
        recorded = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertIn("impl-001", recorded["task_contracts"])


class RigorousReviewNeedsRuntimeEvidence(unittest.TestCase):
    """A self-declared independence string is not enough."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.state_dir = self.root / ".architect-dev-team"
        self.state_dir.mkdir()
        self.addCleanup(self.temp.cleanup)

    def _state(self):
        arch = self.state_dir / "architecture.md"
        arch.write_text("# A\n", encoding="utf-8")
        import hashlib
        digest = hashlib.sha256(arch.read_bytes()).hexdigest()
        review = self.state_dir / "review.json"
        review.write_text(json.dumps({"schema_version": 2, "head_revision": None,
                                      "files": []}), encoding="utf-8")
        return {
            "schema_version": 2, "phase": "VERIFICATION", "approval_stage": None,
            "profile": "rigorous",
            "architecture": {"path": ".architect-dev-team/architecture.md", "sha256": digest},
            "milestone": {"id": "M1", "summary": "s", "acceptance": ["a"],
                          "required_checks": ["unit-tests"]},
            "approvals": [{"kind": "architecture", "decision": "approved",
                           "scope_sha256": "0" * 64, "review_sha256": None,
                           "evidence": "user approved",
                           "recorded_at": "2026-10-20T12:00:00+00:00"}],
            "checks": [{"name": "unit-tests", "required": True, "status": "passed",
                        "evidence": "ran", "waiver": None}],
            "review": {"path": ".architect-dev-team/review.json",
                       "sha256": hashlib.sha256(review.read_bytes()).hexdigest(),
                       "independence": "independent", "evidence": "self declared"},
            "completed": [], "open_issues": [], "constraints": [],
            "next_action": "Review",
        }

    def test_self_declared_independence_is_not_accepted(self):
        from ldt_core.state import state as validate_state
        from ldt_core.approvals import scope
        value = self._state()
        value["approvals"][0]["scope_sha256"] = scope(value)
        with self.assertRaisesRegex(Invalid, "verified runtime evidence"):
            validate_state(value, self.root, "review")

    def test_bound_runtime_evidence_satisfies_the_gate(self):
        from ldt_core.state import state as validate_state
        from ldt_core.approvals import scope
        value = self._state()
        value["approvals"][0]["scope_sha256"] = scope(value)
        evidence = self.state_dir / "integration_evidence.json"
        evidence.write_text(json.dumps({"independence": [{
            "task": "impl-001", "independence": "independent", "reasons": [],
            "evidence": {
                "implementer_session_id": "ses_a",
                "critic_session_id": "ses_b",
                "critic_read_only": True,
                "implementer_execution_mode": "native",
                "critic_execution_mode": "native",
            }}]}), encoding="utf-8")
        import hashlib
        value["review"]["verification"] = {
            "path": ".architect-dev-team/integration_evidence.json",
            "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest()}
        validate_state(value, self.root, "review")

    def test_evidence_with_a_shared_session_is_rejected(self):
        from ldt_core.state import state as validate_state
        from ldt_core.approvals import scope
        value = self._state()
        value["approvals"][0]["scope_sha256"] = scope(value)
        evidence = self.state_dir / "integration_evidence.json"
        evidence.write_text(json.dumps({"independence": [{
            "task": "impl-001", "independence": "independent", "reasons": [],
            "evidence": {
                "implementer_session_id": "ses_same",
                "critic_session_id": "ses_same",
                "critic_read_only": True,
                "implementer_execution_mode": "native",
                "critic_execution_mode": "native",
            }}]}), encoding="utf-8")
        import hashlib
        value["review"]["verification"] = {
            "path": ".architect-dev-team/integration_evidence.json",
            "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest()}
        with self.assertRaisesRegex(Invalid, "verified runtime evidence"):
            validate_state(value, self.root, "review")


class ResearchFixtureIsLabelled(unittest.TestCase):
    """A fixture research run must be visible as such."""

    def test_research_result_carries_execution_mode(self):
        from ldt_core.research import ResearchResult
        result = ResearchResult(task_id="research-001", role="Research", question="q",
                                architecture_version="v1", date="2026-10-20",
                                sources=[], findings={}, assumptions=[], conflicts=[],
                                applicability_limits=[], recommendation="r",
                                confidence="Low", blocking_decisions=[])
        self.assertEqual(result.execution_mode, "native")
        self.assertIn("execution_mode", result.to_dict() if hasattr(result, "to_dict")
                      else result.__dict__)

    def test_architecture_integration_excludes_fixture_research(self):
        """Fixture research must not be folded into the architecture document."""
        from ldt_core import arch_team
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / ".architect-dev-team"
            research_dir = state / "research"
            research_dir.mkdir(parents=True)
            (research_dir / "research-001.md").write_text("findings", encoding="utf-8")
            (research_dir / "research-001.json").write_text(
                json.dumps({"execution_mode": "fixture"}), encoding="utf-8")
            plan = arch_team.ArchitectureTeamPlan(
                architecture_version="v1", brief_version="brief",
                research_tasks=[arch_team.ResearchTask(
                    task_id="research-001", role="Research", question="q", context="c",
                    required_outputs=[], sources=[], deliverable_template="t",
                    review_criteria=[], status="completed",
                    result_path=".architect-dev-team/research/research-001.md")])
            template = root / "arch.md"
            template.write_text("# A\n\n## Design\n\noriginal\n", encoding="utf-8")
            result = arch_team.integrate_research(plan, root, template)
            self.assertNotIn("### research-001", result,
                             "fixture research must not enter the architecture")
            self.assertIn("__excluded_fixture__", result,
                          "excluded fixture research must be reported separately")


if __name__ == "__main__":
    unittest.main()
