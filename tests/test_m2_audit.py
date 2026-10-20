"""Audit tests: real vs simulated agent execution, forged independence,
contract tampering, stale approvals, repair exhaustion, backward compatibility.

These tests never assert on simulated output as if it were native delegation.
They assert that the runtime adapter reports the truth and that forged
evidence is rejected.
"""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / ".agents/skills/architect-dev-team/scripts"
sys.path.insert(0, str(SCRIPTS))

from ldt_core import runtime as rt  # noqa: E402
from ldt_core.common import Invalid  # noqa: E402
from ldt_core.task_contracts import (  # noqa: E402
    TaskContract, CriticContract, load_contract, save_contract, validate_contract,
)


class TestRuntimeDetection(unittest.TestCase):
    """Runtime detection must report honestly, never fabricate availability."""

    def test_detect_runtime_reports_binary_and_version(self):
        info = rt.detect_runtime(refresh=True)
        self.assertIsInstance(info.available, bool)
        if info.available:
            self.assertTrue(info.executable)
            self.assertTrue(info.version)
            self.assertIsNone(info.reason)
        else:
            self.assertTrue(info.reason, "unavailable runtime must state a reason")

    def test_model_candidates_only_use_reported_models(self):
        reported = ["opencode/nemotron-3.5-super-vl-free", "openai/gpt-6.1-sol"]
        chain = rt.model_candidates("high", reported)
        self.assertTrue(chain, "a reported model must produce a candidate")
        for model in chain:
            self.assertIn(model, reported)
        self.assertEqual(rt.model_candidates("high", []), [])

    def test_model_candidates_never_invent_identifiers(self):
        reported = ["opencode/minimax-m3.1-flash-free"]
        chain = rt.model_candidates("medium", reported)
        self.assertTrue(chain, "a reported model must produce a candidate")
        for model in chain:
            self.assertIn(model, reported)
        # A profile with no matching needle yields no invented identifier.
        self.assertEqual(rt.model_candidates("high", ["totally/unrelated-model"]), [])

    def test_model_candidates_prefer_stronger_models_for_high(self):
        reported = ["opencode/minimax-m3.1-flash-free",
                    "opencode/nemotron-3.5-super-vl-free"]
        chain = rt.model_candidates("high", reported)
        self.assertEqual(chain[0], "opencode/nemotron-3.5-super-vl-free")

    def test_role_to_native_agent_mapping_is_read_only_for_critics(self):
        self.assertEqual(rt.agent_for_role("Independent Critic"), "explore")
        self.assertEqual(rt.agent_for_role("research"), "explore")
        self.assertEqual(rt.agent_for_role("Backend Specialist"), "general")
        self.assertTrue(rt.is_read_only_agent(rt.agent_for_role("critic")))
        self.assertFalse(rt.is_read_only_agent(rt.agent_for_role("implementer")))

    def test_dispatch_without_runtime_reports_unavailable(self):
        with mock.patch.object(rt, "_resolve_executable", return_value=None):
            run = rt.dispatch("prompt", "implementer", Path("."))
        self.assertEqual(run.status, "unavailable")
        self.assertIsNone(run.session_id)
        self.assertIn("not found", (run.error or "").lower())


class TestIndependenceVerification(unittest.TestCase):
    """Independence must be derived from verifiable runtime evidence."""

    def _run(self, session, agent, status="completed"):
        return rt.AgentRun(status=status, session_id=session, agent=agent, model="m")

    def test_missing_session_ids_fail_independence(self):
        report = rt.independence_report(self._run(None, "general"), self._run(None, "explore"))
        self.assertEqual(report["independence"], "unavailable")
        self.assertTrue(any("session id" in r for r in report["reasons"]))

    def test_shared_session_fails_independence(self):
        with mock.patch.object(rt, "verify_session", return_value={"verified": True, "agent": "explore"}):
            report = rt.independence_report(
                self._run("ses_same", "general"), self._run("ses_same", "explore"))
        self.assertEqual(report["independence"], "unavailable")
        self.assertTrue(any("same session" in r for r in report["reasons"]))

    def test_unverifiable_session_fails_independence(self):
        with mock.patch.object(rt, "verify_session", return_value={"verified": False, "reason": "gone"}):
            report = rt.independence_report(
                self._run("ses_a", "general"), self._run("ses_b", "explore"))
        self.assertEqual(report["independence"], "unavailable")
        self.assertTrue(any("not verifiable" in r for r in report["reasons"]))

    def test_writable_critic_agent_fails_independence(self):
        def verify(session_id, cwd=None):
            return {"verified": True, "agent": "general" if session_id == "ses_a" else "general"}
        with mock.patch.object(rt, "verify_session", side_effect=verify):
            report = rt.independence_report(
                self._run("ses_a", "general"), self._run("ses_b", "general"))
        self.assertEqual(report["independence"], "unavailable")
        self.assertTrue(any("not read-only" in r for r in report["reasons"]))

    def test_distinct_verified_read_only_critic_passes(self):
        def verify(session_id, cwd=None):
            return {"verified": True, "agent": "general" if session_id == "ses_a" else "explore",
                    "tokens": {"input": 10, "output": 5}}
        with mock.patch.object(rt, "verify_session", side_effect=verify):
            report = rt.independence_report(
                self._run("ses_a", "general"), self._run("ses_b", "explore"))
        self.assertEqual(report["independence"], "independent")
        self.assertEqual(report["reasons"], [])
        self.assertEqual(report["critic"]["agent"], "explore")

    def test_unavailable_runtime_cannot_yield_independence(self):
        report = rt.independence_report(
            self._run(None, "general", status="unavailable"),
            self._run(None, "explore", status="unavailable"))
        self.assertEqual(report["independence"], "unavailable")
        self.assertTrue(any("runtime unavailable" in r for r in report["reasons"]))


class TestContractIntegrity(unittest.TestCase):
    """Contract tampering and policy violations must be detected."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _contract(self, **overrides):
        data = dict(
            task_id="impl-001", role="Backend Specialist", goal="Implement API",
            architecture_version="v1", milestone_id="M1", base_revision="a" * 40,
            acceptance=["works"], required_checks=["unit-tests"],
            resource_budget={"tokens": 1000, "time_seconds": 60},
        )
        data.update(overrides)
        return TaskContract(**data)

    def test_missing_required_field_is_reported(self):
        contract = self._contract(goal="")
        errors = validate_contract(contract, ["unit-tests"], [])
        self.assertTrue(any("goal" in e for e in errors))

    def test_check_outside_milestone_policy_is_rejected(self):
        contract = self._contract(required_checks=["unit-tests", "smuggled"])
        errors = validate_contract(contract, ["unit-tests"], [])
        self.assertTrue(any("not in milestone.required_checks" in e for e in errors))

    def test_unapproved_skill_pin_is_rejected(self):
        contract = self._contract(skill_pins=["unknown-skill@abc"])
        errors = validate_contract(contract, ["unit-tests"], ["approved-skill"])
        self.assertTrue(any("not in approved skills" in e for e in errors))

    def test_invalid_model_profile_is_rejected(self):
        contract = self._contract(model_profile="turbo")
        errors = validate_contract(contract, ["unit-tests"], [])
        self.assertTrue(any("model_profile" in e for e in errors))

    def test_missing_resource_budget_is_rejected(self):
        contract = self._contract(resource_budget={})
        errors = validate_contract(contract, ["unit-tests"], [])
        self.assertTrue(any("tokens" in e for e in errors))

    def test_critic_contract_requires_review_target(self):
        contract = CriticContract(task_id="critic-001", review_target="",
                                  architecture_version="v1", milestone_id="M1",
                                  base_revision="a" * 40)
        errors = validate_contract(contract, ["pair-review"], [])
        self.assertTrue(any("review_target" in e for e in errors))

    def test_critic_contract_is_prohibited_from_writing_production(self):
        contract = CriticContract(task_id="critic-001", review_target="impl-001",
                                  architecture_version="v1", milestone_id="M1",
                                  base_revision="a" * 40)
        self.assertIn("write:src/**", contract.prohibited_actions)
        self.assertIn("file:line references", contract.evidence_requirements)

    def test_roundtrip_preserves_runtime_evidence(self):
        contract = self._contract(session_id="ses_abc", agent="general", model="m")
        save_contract(contract, self.root)
        loaded = load_contract(self.root, "impl-001")
        self.assertEqual(loaded.session_id, "ses_abc")
        self.assertEqual(loaded.agent, "general")
        self.assertEqual(loaded.model, "m")

    def test_tampered_contract_is_detectable_by_digest(self):
        """A changed contract must not pass a digest comparison."""
        contract = self._contract()
        save_contract(contract, self.root)
        path = self.root / ".architect-dev-team" / "tasks" / "impl-001.json"
        original = path.read_bytes()
        original_digest = hashlib.sha256(original).hexdigest()

        data = json.loads(original)
        data["goal"] = "Something else entirely"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        self.assertNotEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                            original_digest,
                            "a tampered contract must change the digest")
        loaded = load_contract(self.root, "impl-001")
        self.assertNotEqual(loaded.goal, contract.goal)


class TestRepairLoopBound(unittest.TestCase):
    """The repair loop must be bounded and report exhaustion."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_repair_loop_stops_at_budget_and_records_exhaustion(self):
        from ldt_core import pair_execution as pe

        contract = TaskContract(task_id="impl-001", role="Backend Specialist",
                                goal="g", architecture_version="v1", milestone_id="M1",
                                base_revision="a" * 40, acceptance=["x"],
                                required_checks=["unit-tests"],
                                resource_budget={"tokens": 1, "time_seconds": 1})

        calls = {"n": 0}

        def fake_dispatch(root, c, prompt):
            calls["n"] += 1
            return rt.AgentRun(status="completed", session_id=f"ses_{calls['n']}",
                              agent="general", model="m", output="{}")

        def fake_critic(root, c, impl_result, **kwargs):
            return rt.AgentRun(status="completed", session_id="ses_critic",
                               agent="explore", model="m",
                               output=json.dumps({
                                   "task_id": c.task_id,
                                   "reviewed_task_id": c.review_target,
                                   "reviewed_revision": pe._current_revision(self.root),
                                   "reviewer": {"session_id": "ses_critic", "agent": "explore",
                                                "model": "m", "execution_mode": "native",
                                                "verified": True, "read_only_agent": True},
                                   "coverage": {"requirements_checked": ["r"],
                                                "files_inspected": ["src/a.py"],
                                                "interfaces_checked": [],
                                                "evidence_references": [],
                                                "checks_run": [{"name": "c", "result": "failed",
                                                                "evidence": "failed"}],
                                                "unverified_areas": []},
                                   "findings": [{"severity": "major", "file": "src/a.py", "line": 1,
                                                 "issue": "still broken", "reproduction": "x",
                                                 "reference": "y"}],
                                   "verified_non_findings": [],
                                   "confidence": "medium", "limitations": [],
                                   "recommendation": "reject", "summary": "still broken"}))

        verified = {"verified": True, "agent": "explore", "read_only_agent": True}
        with mock.patch.object(pe, "dispatch_subagent", side_effect=fake_dispatch), \
             mock.patch.object(pe, "run_critic", side_effect=fake_critic), \
             mock.patch.object(pe, "verify_session", return_value=verified):
            final, trail = pe.repair_loop(self.root, contract,
                                          {"findings": [{"file": "src/a.py"}]},
                                          max_rounds=2, revision=pe._current_revision(self.root))

        exhaust = [t for t in trail if t.get("outcome") == "repair_budget_exhausted"]
        self.assertTrue(exhaust, trail)
        self.assertEqual(exhaust[0]["rounds"], 2)
        # One initial review plus at most two repair rounds.
        self.assertLessEqual(calls["n"], 2)

    def test_resolved_group_stops_early(self):
        from ldt_core import pair_execution as pe

        contract = TaskContract(task_id="impl-001", role="Backend Specialist",
                                goal="g", architecture_version="v1", milestone_id="M1",
                                base_revision="a" * 40, acceptance=["x"],
                                required_checks=["unit-tests"],
                                resource_budget={"tokens": 1, "time_seconds": 1})

        calls = {"n": 0}

        def fake_dispatch(root, c, prompt):
            calls["n"] += 1
            return rt.AgentRun(status="completed", session_id="ses_r", agent="general",
                              model="m", output="{}")

        def fake_critic(root, c, impl_result, **kwargs):
            return rt.AgentRun(status="completed", session_id="ses_c", agent="explore",
                               model="m",
                               output=json.dumps({
                                   "task_id": c.task_id,
                                   "reviewed_task_id": c.review_target,
                                   "reviewed_revision": pe._current_revision(self.root),
                                   "reviewer": {"session_id": "ses_c", "agent": "explore",
                                                "model": "m", "execution_mode": "native",
                                                "verified": True, "read_only_agent": True},
                                   "coverage": {"requirements_checked": ["r"],
                                                "files_inspected": ["src/a.py"],
                                                "interfaces_checked": [],
                                                "evidence_references": [],
                                                "checks_run": [{"name": "c", "result": "passed",
                                                                "evidence": "ok"}],
                                                "unverified_areas": []},
                                   "findings": [],
                                   "verified_non_findings": ["looks right"],
                                   "confidence": "high", "limitations": [],
                                   "recommendation": "approve", "summary": "fine"}))

        verified = {"verified": True, "agent": "explore", "read_only_agent": True}
        with mock.patch.object(pe, "dispatch_subagent", side_effect=fake_dispatch), \
             mock.patch.object(pe, "run_critic", side_effect=fake_critic), \
             mock.patch.object(pe, "verify_session", return_value=verified):
            final, trail = pe.repair_loop(self.root, contract,
                                          {"findings": [{"file": "src/a.py"}]},
                                          max_rounds=2, revision=pe._current_revision(self.root))

        self.assertEqual(calls["n"], 1)
        self.assertTrue(any(t.get("outcome") == "resolved" for t in trail), trail)

    def test_agent_output_that_is_not_json_is_not_fabricated_into_findings(self):
        from ldt_core import pair_execution as pe
        run = rt.AgentRun(status="completed", session_id="ses_x", agent="general",
                          model="m", output="I could not do the task, sorry.")
        data = pe._parse_agent_output(run)
        self.assertEqual(data["findings"], [])
        self.assertIn("raw_output", data["evidence"])


class TestBackwardCompatibility(unittest.TestCase):
    """M1a-M1d state and contracts must keep working."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state_dir = self.root / ".architect-dev-team"
        self.state_dir.mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def _state(self, **overrides):
        data = {
            "schema_version": 2, "phase": "INTAKE", "approval_stage": None,
            "profile": "balanced", "architecture": None, "milestone": None,
            "approvals": [], "checks": [], "review": None, "completed": [],
            "open_issues": [], "constraints": [], "next_action": "Inspect",
        }
        data.update(overrides)
        return data

    def test_state_without_new_fields_is_accepted(self):
        from ldt_core.state import state
        value = self._state()
        state(value, self.root)  # must not raise

    def test_state_with_new_fields_is_accepted(self):
        from ldt_core.state import state
        value = self._state(brief=None, research_results=[], task_contracts=[],
                            project_view=None, pair_results=[], lead_session=None,
                            arch_lead_session=None,
                            effort={"tokens": 0, "time_seconds": 0, "agents": 0,
                                    "repair_rounds": 0})
        state(value, self.root)  # must not raise

    def test_new_fields_do_not_change_scope_fingerprint(self):
        from ldt_core.state import scope
        base = self._state()
        extended = dict(base, brief="x", task_contracts=[{"task_id": "t"}],
                        project_view={"status": "Entwurf"})
        self.assertEqual(scope(base), scope(extended))

    def test_legacy_registry_still_validates(self):
        from ldt_core.registry import registry_file
        legacy = REPO / ".agents/skills/architect-dev-team/registry/skills.json"
        registry_file(legacy)  # must not raise

    def test_legacy_registry_bytes_are_unchanged(self):
        legacy = REPO / ".agents/skills/architect-dev-team/registry/skills.json"
        data = json.loads(legacy.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["skills"][0]["id"], "openai-gh-fix-ci")


class TestIntegrationGate(unittest.TestCase):
    """Integration must not report success without real evidence."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_independence_is_unavailable_without_sessions(self):
        from ldt_core.integration import check_review_independence
        from ldt_core.task_contracts import TaskContract
        task = TaskContract(task_id="impl-001", role="Backend Specialist", goal="g",
                            architecture_version="v1", milestone_id="M1",
                            base_revision="a" * 40, status="completed")
        results = check_review_independence(self.root, [{"task": task, "critic": None}])
        self.assertEqual(results[0]["independence"], "unavailable")
        self.assertTrue(results[0]["reasons"])

    def test_failed_test_command_is_not_reported_as_passed(self):
        from ldt_core.integration import run_integration_tests
        results = run_integration_tests(self.root, ['"{}" -c "import sys; sys.exit(3)"'.format(sys.executable)])
        self.assertTrue(results, "the runner must produce a result entry")
        for value in results.values():
            self.assertFalse(value["passed"])
            self.assertEqual(value["exit_code"], 3)

    def test_missing_test_suite_is_a_failure_not_a_pass(self):
        from ldt_core.integration import run_integration_tests
        results = run_integration_tests(self.root, ['"{}" -m pytest nonexistent_dir/ -v'.format(sys.executable)])
        self.assertTrue(results, "the runner must produce a result entry")
        for value in results.values():
            self.assertFalse(value["passed"])


if __name__ == "__main__":
    unittest.main()
