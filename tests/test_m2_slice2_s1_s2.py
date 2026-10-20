"""Focused tests for M2 Slice 2 S1 (Department Lead) and S2 (CriticReport).

Deterministic unit tests with a stubbed runtime. The real-agent behaviour is
verified separately by tools/e2e_lead_critic.py, which is not part of the
standard regression suite.
"""
import json
import os
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
from ldt_core.common import Invalid  # noqa: E402
from ldt_core.runtime import AgentRun  # noqa: E402
from ldt_core.task_contracts import (  # noqa: E402
    CriticContract, LeadContract, LeadResult, TaskContract,
    create_critic_contract, create_lead_contract, load_contract, save_contract,
    validate_contract,
)


def a_valid_report(**overrides):
    data = {
        "task_id": "critic-001",
        "reviewed_task_id": "impl-001",
        "reviewed_revision": "rev-1",
        "reviewer": {
            "session_id": "ses_critic", "agent": "explore", "model": "m",
            "execution_mode": "native", "verified": True, "read_only_agent": True,
        },
        "coverage": {
            "requirements_checked": ["register rejects a duplicate email"],
            "files_inspected": ["src/users.py"],
            "interfaces_checked": ["register()"],
            "evidence_references": ["src/users.py:12"],
            "checks_run": [{"name": "unit-tests", "result": "passed", "evidence": "1 passed"}],
            "unverified_areas": ["concurrency"],
        },
        "findings": [{
            "severity": "major", "file": "src/users.py", "line": 12,
            "issue": "case-sensitive duplicate check", "reproduction": "A@x then a@x",
            "reference": "acceptance: rejects duplicate email",
        }],
        "verified_non_findings": ["invalid email is rejected"],
        "confidence": "medium",
        "limitations": ["no concurrency test"],
        "recommendation": "approve_with_findings",
        "summary": "One major finding on the duplicate check.",
    }
    data.update(overrides)
    return data


class CriticReportParsing(unittest.TestCase):
    """A report must be a well formed JSON object."""

    def test_valid_report_parses(self):
        report = cr.parse_critic_report(json.dumps(a_valid_report()))
        self.assertEqual(report.task_id, "critic-001")
        self.assertEqual(report.reviewer.session_id, "ses_critic")
        self.assertEqual(len(report.findings), 1)

    def test_prose_around_json_is_accepted_at_the_parse_level(self):
        """A short remark or code fence does not hide the report.

        The content is still validated strictly afterwards, so a lenient
        extraction never means a lenient verdict.
        """
        report = cr.parse_critic_report("Here is my review: " + json.dumps(a_valid_report()))
        self.assertEqual(report.task_id, "critic-001")
        report = cr.parse_critic_report(
            "```json\n" + json.dumps(a_valid_report()) + "\n```")
        self.assertEqual(report.task_id, "critic-001")

    def test_an_incomplete_json_object_is_rejected(self):
        for broken in ('{"a": 1', "no json at all", "{", "}{"):
            with self.subTest(broken=broken):
                with self.assertRaises(Invalid):
                    cr.parse_critic_report(broken)

    def test_a_json_array_is_rejected(self):
        with self.assertRaises(Invalid):
            cr.parse_critic_report("[1, 2, 3]")

    def test_extraction_ignores_braces_inside_strings(self):
        data = cr.extract_json_object('{"a": "}"}{"b": 2}')
        self.assertEqual(data, {"a": "}"})

    def test_empty_output_is_rejected(self):
        with self.assertRaises(Invalid):
            cr.parse_critic_report("")

    def test_non_object_is_rejected(self):
        with self.assertRaises(Invalid):
            cr.parse_critic_report("[1, 2, 3]")

    def test_wrong_types_are_rejected(self):
        for broken in ({"findings": "not a list"},
                       {"coverage": "not an object"},
                       {"reviewer": []},
                       {"verified_non_findings": {}},
                       {"limitations": 5}):
            with self.subTest(broken=broken):
                with self.assertRaises(Invalid):
                    cr.parse_critic_report(json.dumps(a_valid_report(**broken)))


class CriticReportValidation(unittest.TestCase):
    """Every rejection the contract requires."""

    def _errors(self, report, **overrides):
        kwargs = dict(
            expected_task_id="critic-001",
            expected_reviewed_task_id="impl-001",
            expected_revision="rev-1",
            implementer_session_id="ses_impl",
        )
        kwargs.update(overrides)
        return cr.validate_critic_report(report, **kwargs)

    def test_a_complete_report_passes(self):
        report = cr.parse_critic_report(json.dumps(a_valid_report()))
        self.assertEqual(self._errors(report), [])

    def test_missing_execution_evidence_is_rejected(self):
        report = cr.parse_critic_report(json.dumps(a_valid_report()))
        report.reviewer.session_id = ""
        self.assertTrue(any("session id" in e for e in self._errors(report)))

    def test_unverified_reviewer_is_rejected(self):
        report = cr.parse_critic_report(json.dumps(a_valid_report()))
        report.reviewer.verified = False
        self.assertTrue(any("not verified" in e for e in self._errors(report)))

    def test_writable_reviewer_is_rejected(self):
        report = cr.parse_critic_report(json.dumps(a_valid_report()))
        report.reviewer.read_only_agent = False
        self.assertTrue(any("not read-only" in e for e in self._errors(report)))

    def test_fixture_execution_is_rejected(self):
        report = cr.parse_critic_report(json.dumps(a_valid_report()))
        report.reviewer.execution_mode = "fixture"
        self.assertTrue(any("native agent run" in e for e in self._errors(report)))

    def test_implementer_session_as_reviewer_is_rejected(self):
        report = cr.parse_critic_report(json.dumps(a_valid_report()))
        report.reviewer.session_id = "ses_impl"
        self.assertTrue(any("implementer session" in e for e in self._errors(report)))

    def test_stale_revision_is_rejected(self):
        report = cr.parse_critic_report(json.dumps(a_valid_report()))
        report.reviewed_revision = "rev-old"
        self.assertTrue(any("bound to revision" in e for e in self._errors(report)))

    def test_wrong_reviewed_task_is_rejected(self):
        report = cr.parse_critic_report(json.dumps(a_valid_report()))
        report.reviewed_task_id = "other"
        self.assertTrue(any("reviewed_task_id" in e for e in self._errors(report)))

    def test_missing_coverage_is_rejected(self):
        report = cr.parse_critic_report(json.dumps(a_valid_report()))
        report.coverage.requirements_checked = []
        self.assertTrue(any("checked requirements" in e for e in self._errors(report)))
        report.coverage.files_inspected = []
        self.assertTrue(any("inspected files" in e for e in self._errors(report)))

    def test_claim_without_execution_evidence_is_rejected(self):
        report = cr.parse_critic_report(json.dumps(a_valid_report()))
        report.coverage.checks_run = [{"name": "unit-tests", "result": "passed", "evidence": ""}]
        self.assertTrue(any("without evidence" in e for e in self._errors(report)))

    def test_invalid_file_reference_is_rejected(self):
        report = cr.parse_critic_report(json.dumps(a_valid_report()))
        report.coverage.files_inspected = ["../outside.py"]
        self.assertTrue(any("invalid file reference" in e for e in self._errors(report)))

    def test_blocking_finding_cannot_be_approved_away(self):
        report = cr.parse_critic_report(json.dumps(a_valid_report()))
        report.findings[0].severity = "blocker"
        report.recommendation = "approve"
        self.assertTrue(any("blocking" in e for e in self._errors(report)))

    def test_missing_findings_and_non_findings_is_rejected(self):
        report = cr.parse_critic_report(json.dumps(a_valid_report()))
        report.findings = []
        report.verified_non_findings = []
        self.assertTrue(any("neither a finding" in e for e in self._errors(report)))

    def test_invalid_confidence_and_recommendation_are_rejected(self):
        report = cr.parse_critic_report(json.dumps(a_valid_report()))
        report.confidence = "very high"
        self.assertTrue(any("confidence" in e for e in self._errors(report)))
        report.confidence = "medium"
        report.recommendation = "looks fine"
        self.assertTrue(any("recommendation" in e for e in self._errors(report)))

    def test_missing_summary_is_rejected(self):
        report = cr.parse_critic_report(json.dumps(a_valid_report()))
        report.summary = ""
        self.assertTrue(any("summary" in e for e in self._errors(report)))

    def test_finding_without_reproduction_is_rejected(self):
        report = cr.parse_critic_report(json.dumps(a_valid_report()))
        report.findings[0].reproduction = ""
        self.assertTrue(any("reproduction" in e for e in self._errors(report)))


class CriticContractScope(unittest.TestCase):
    """The critic contract must declare what it has to cover."""

    def test_critic_without_requirements_is_invalid(self):
        contract = create_critic_contract(
            task_id="critic-001", review_target="impl-001",
            architecture_version="v1", milestone_id="M1", base_revision="a" * 40)
        errors = validate_contract(contract, ["unit-tests"], [])
        self.assertTrue(any("requirements" in e for e in errors))

    def test_critic_with_requirements_is_valid(self):
        contract = create_critic_contract(
            task_id="critic-001", review_target="impl-001",
            architecture_version="v1", milestone_id="M1", base_revision="a" * 40,
            requirements=["rejects duplicate email"], files_in_scope=["src/users.py"])
        errors = validate_contract(contract, ["unit-tests"], [])
        self.assertEqual(errors, [])

    def test_critic_does_not_preclaim_independence(self):
        contract = create_critic_contract(
            task_id="critic-001", review_target="impl-001",
            architecture_version="v1", milestone_id="M1", base_revision="a" * 40,
            requirements=["x"])
        self.assertEqual(contract.independence, "unavailable")


class LeadPlanValidation(unittest.TestCase):
    """The lead's plan must be bounded and consistent."""

    def setUp(self):
        self.contract = create_lead_contract(
            task_id="lead-1", outcome="Deliver the slice",
            architecture_path=".architect-dev-team/architecture.md",
            architecture_sha256="a" * 64, milestone_id="M1", base_revision="b" * 40,
            acceptance=["works"], required_checks=["unit-tests"],
            resource_budget={"tokens": 1000, "time_seconds": 60},
            max_specialists=3)
        self.roster = [
            {"task_id": "impl-001",
             "file_ownership": {"src/api.py": "impl-001"}},
            {"task_id": "impl-002",
             "file_ownership": {"src/db.py": "impl-002"}},
        ]

    def _plan(self, **overrides):
        plan = {
            "validates_against_architecture": True,
            "architecture_conflicts": [],
            "missing_information": [],
            "risks": [],
            "assignments": [{
                "task_id": "impl-001", "role": "Backend",
                "goal": "Implement the endpoint",
                "file_ownership": {"src/api.py": "impl-001"},
                "acceptance": ["returns 200"], "required_checks": ["unit-tests"],
                "model_profile": "medium", "review_assignment": "critic-001",
                "skill_pins": [],
            }],
            "plan_summary": "One specialist.",
        }
        plan.update(overrides)
        return plan

    def test_a_valid_plan_passes(self):
        self.assertEqual(le.validate_lead_plan(self._plan(), self.contract, self.roster), [])

    def test_overlapping_file_ownership_is_rejected(self):
        plan = self._plan()
        plan["assignments"].append({
            "task_id": "impl-002", "role": "Frontend",
            "goal": "Implement the view",
            "file_ownership": {"src/api.py": "impl-002"},
            "acceptance": ["renders"], "required_checks": ["unit-tests"],
            "model_profile": "medium", "review_assignment": "critic-001",
            "skill_pins": [],
        })
        errors = le.validate_lead_plan(plan, self.contract, self.roster)
        self.assertTrue(any("claimed by" in e for e in errors))

    def test_more_specialists_than_the_budget_is_rejected(self):
        plan = self._plan()
        plan["assignments"] = [dict(plan["assignments"][0], task_id=f"impl-{i:03d}")
                               for i in range(5)]
        errors = le.validate_lead_plan(plan, self.contract, self.roster)
        self.assertTrue(any("budget" in e for e in errors))

    def test_task_outside_the_roster_is_rejected(self):
        plan = self._plan()
        plan["assignments"][0]["task_id"] = "impl-999"
        errors = le.validate_lead_plan(plan, self.contract, self.roster)
        self.assertTrue(any("not part of the agreed roster" in e for e in errors))

    def test_assignment_without_acceptance_is_rejected(self):
        plan = self._plan()
        plan["assignments"][0]["acceptance"] = []
        errors = le.validate_lead_plan(plan, self.contract, self.roster)
        self.assertTrue(any("acceptance criteria" in e for e in errors))

    def test_assignment_without_checks_is_rejected(self):
        plan = self._plan()
        plan["assignments"][0]["required_checks"] = []
        errors = le.validate_lead_plan(plan, self.contract, self.roster)
        self.assertTrue(any("required checks" in e for e in errors))

    def test_assignment_without_reviewer_is_rejected(self):
        plan = self._plan()
        plan["assignments"][0]["review_assignment"] = ""
        errors = le.validate_lead_plan(plan, self.contract, self.roster)
        self.assertTrue(any("no reviewer" in e for e in errors))

    def test_invalid_model_profile_is_rejected(self):
        plan = self._plan()
        plan["assignments"][0]["model_profile"] = "turbo"
        errors = le.validate_lead_plan(plan, self.contract, self.roster)
        self.assertTrue(any("model profile" in e for e in errors))

    def test_conflict_with_architecture_blocks_assignments(self):
        plan = self._plan(validates_against_architecture=False)
        errors = le.validate_lead_plan(plan, self.contract, self.roster)
        self.assertTrue(any("architecture conflict" in e for e in errors))


class LeadOrchestration(unittest.TestCase):
    """The lead must actually delegate and the core must enforce the bounds."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.contract = create_lead_contract(
            task_id="lead-1", outcome="Deliver the slice",
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

    def _review(self, accepted=True, decision="accept"):
        return json.dumps({
            "accepted": accepted,
            "decisions": [{"task_id": "impl-001", "decision": decision,
                            "reason": "ok", "correction": {"goal": "", "checks": []}}],
            "unresolved": [], "escalated": False,
            "summary": "Accepted.",
        })

    def test_lead_delegates_to_a_real_specialist(self):
        """The lead plans, the specialist runs, the lead accepts."""
        calls = []

        def fake_dispatch(prompt, role, cwd, **kwargs):
            calls.append((role, prompt))
            if "plan" in kwargs.get("title", ""):
                return AgentRun(status="completed", session_id="ses_plan",
                                agent="general", model="m", output=self._plan())
            if role == "Backend":
                return AgentRun(status="completed", session_id="ses_spec",
                                agent="general", model="m",
                                output=json.dumps({"status": "completed", "changes": [],
                                                   "acceptance_met": True,
                                                   "findings": [],
                                                   "evidence": {"unit-tests": "1 passed"},
                                                   "checks": [{"name": "unit-tests",
                                                               "result": "passed",
                                                               "evidence": "1 passed"}],
                                                   "risks": [],
                                                   "unresolved": [], "summary": "done"}))
            return AgentRun(status="completed", session_id="ses_review",
                            agent="general", model="m", output=self._review())

        with mock.patch.object(le, "dispatch", side_effect=fake_dispatch):
            result = le.run_department_lead(self.root, self.contract, self.roster, "# Arch")

        self.assertTrue(result.accepted)
        self.assertEqual(result.status, "completed")
        self.assertEqual(len(result.specialists), 1)
        self.assertEqual(result.specialists[0]["session_id"], "ses_spec")
        # The specialist contract really exists on disk.
        self.assertTrue((self.root / ".architect-dev-team" / "tasks" / "impl-001.json").exists())
        roles = [c[0] for c in calls]
        self.assertIn("department_lead", roles)
        self.assertIn("Backend", roles)

    def test_a_specialist_without_evidence_is_not_accepted(self):
        """The core decides, not the lead's own flag."""
        def fake_dispatch(prompt, role, cwd, **kwargs):
            title = kwargs.get("title", "")
            if "plan" in title:
                return AgentRun(status="completed", session_id="ses_plan",
                                agent="general", model="m", output=self._plan())
            if role == "Backend":
                return AgentRun(status="completed", session_id="ses_spec",
                                agent="general", model="m",
                                output=json.dumps({"status": "completed", "changes": [],
                                                   "acceptance_met": True,
                                                   "findings": [], "evidence": {},
                                                   "checks": [], "risks": [],
                                                   "unresolved": [], "summary": "done"}))
            # The lead claims acceptance even though the evidence is missing.
            return AgentRun(status="completed", session_id="ses_review",
                            agent="general", model="m", output=self._review())

        with mock.patch.object(le, "dispatch", side_effect=fake_dispatch):
            result = le.run_department_lead(self.root, self.contract, self.roster, "# Arch")
        self.assertFalse(result.accepted)
        self.assertTrue(result.escalated)

    def test_a_failed_specialist_is_never_accepted(self):
        def fake_dispatch(prompt, role, cwd, **kwargs):
            title = kwargs.get("title", "")
            if "plan" in title:
                return AgentRun(status="completed", session_id="ses_plan",
                                agent="general", model="m", output=self._plan())
            if role == "Backend":
                return AgentRun(status="failed", session_id="ses_spec",
                                agent="general", model="m", error="provider error")
            return AgentRun(status="completed", session_id="ses_review",
                            agent="general", model="m", output=self._review())

        with mock.patch.object(le, "dispatch", side_effect=fake_dispatch):
            result = le.run_department_lead(self.root, self.contract, self.roster, "# Arch")
        self.assertFalse(result.accepted)
        self.assertTrue(result.escalated)

    def test_lead_without_a_valid_plan_is_escalated(self):
        def fake_dispatch(prompt, role, cwd, **kwargs):
            return AgentRun(status="completed", session_id="s", agent="general",
                            model="m", output="not json")
        with mock.patch.object(le, "dispatch", side_effect=fake_dispatch):
            result = le.run_department_lead(self.root, self.contract, self.roster, "# Arch")
        self.assertTrue(result.escalated)
        self.assertFalse(result.accepted)

    def test_lead_reports_an_architecture_conflict(self):
        plan = json.dumps({"validates_against_architecture": False,
                           "architecture_conflicts": ["the outcome needs a database"],
                           "missing_information": [], "risks": [], "assignments": [],
                           "plan_summary": "Blocked."})

        def fake_dispatch(prompt, role, cwd, **kwargs):
            return AgentRun(status="completed", session_id="s", agent="general",
                            model="m", output=plan)
        with mock.patch.object(le, "dispatch", side_effect=fake_dispatch):
            result = le.run_department_lead(self.root, self.contract, self.roster, "# Arch")
        self.assertTrue(result.escalated)
        self.assertEqual(result.status, "blocked")
        self.assertTrue(any("database" in u for u in result.unresolved))

    def test_bounded_correction_rounds(self):
        """A rejected specialist is corrected, at most max_correction_rounds times."""
        rounds = {"n": 0}

        def fake_dispatch(prompt, role, cwd, **kwargs):
            title = kwargs.get("title", "")
            if "plan" in title:
                return AgentRun(status="completed", session_id="ses_plan",
                                agent="general", model="m", output=self._plan())
            if role == "Backend":
                rounds["n"] += 1
                return AgentRun(status="completed", session_id=f"ses_spec{rounds['n']}",
                                agent="general", model="m",
                                output=json.dumps({"status": "completed", "changes": [],
                                                   "acceptance_met": False,
                                                   "findings": [],
                                                   "evidence": {"unit-tests": "failed"},
                                                   "checks": [{"name": "unit-tests",
                                                               "result": "failed",
                                                               "evidence": "failed"}],
                                                   "risks": [],
                                                   "unresolved": [], "summary": "partial"}))
            # The lead always rejects until the budget is exhausted.
            return AgentRun(status="completed", session_id="ses_review",
                            agent="general", model="m",
                            output=self._review(accepted=False, decision="reject"))

        with mock.patch.object(le, "dispatch", side_effect=fake_dispatch):
            result = le.run_department_lead(self.root, self.contract, self.roster, "# Arch")

        # One initial run plus at most max_correction_rounds corrections.
        self.assertEqual(rounds["n"], self.contract.max_correction_rounds + 1)
        self.assertEqual(result.rounds_used, self.contract.max_correction_rounds)
        self.assertTrue(result.corrections)
        self.assertFalse(result.accepted)

    def test_specialist_failure_is_recorded_not_hidden(self):
        def fake_dispatch(prompt, role, cwd, **kwargs):
            title = kwargs.get("title", "")
            if "plan" in title:
                return AgentRun(status="completed", session_id="ses_plan",
                                agent="general", model="m", output=self._plan())
            if role == "Backend":
                return AgentRun(status="failed", session_id="ses_spec",
                                agent="general", model="m", error="provider error")
            return AgentRun(status="completed", session_id="ses_review",
                            agent="general", model="m", output=self._review())

        with mock.patch.object(le, "dispatch", side_effect=fake_dispatch):
            result = le.run_department_lead(self.root, self.contract, self.roster, "# Arch")
        self.assertEqual(result.specialists[0]["status"], "failed")
        self.assertFalse(result.specialists[0]["acceptance_met"])


class DepartmentAcceptance(unittest.TestCase):
    """Acceptance requires outputs, scope, evidence and satisfied review."""

    def test_lead_review_can_reject_for_missing_evidence(self):
        review = json.dumps({
            "accepted": False,
            "decisions": [{"task_id": "impl-001", "decision": "reject",
                            "reason": "the required check has no output",
                            "correction": {"goal": "run unit-tests and report it",
                                           "checks": ["unit-tests"]}}],
            "unresolved": ["unit-tests evidence"], "escalated": False,
            "summary": "Not accepted."})
        data = json.loads(review)
        decision = data["decisions"][0]
        self.assertEqual(decision["decision"], "reject")
        self.assertTrue(decision["correction"]["goal"])
        self.assertIn("unit-tests", decision["correction"]["checks"])

    def test_lead_result_round_trip(self):
        result = LeadResult(lead_task_id="lead-1", status="completed", accepted=True,
                            specialists=[{"task_id": "impl-001"}], rounds_used=1)
        restored = LeadResult.from_dict(result.to_dict())
        self.assertEqual(restored.lead_task_id, "lead-1")
        self.assertTrue(restored.accepted)
        self.assertEqual(restored.rounds_used, 1)

    def test_lead_result_cannot_approve_a_milestone(self):
        """The handoff is a department result, not a human approval."""
        result = LeadResult(lead_task_id="lead-1", status="completed", accepted=True)
        payload = result.to_dict()
        self.assertNotIn("approval", payload)
        self.assertNotIn("approved_scope", payload)


class RuntimeFallbackAndUnavailability(unittest.TestCase):
    """Model fallback and unavailable runtimes stay honest."""

    def test_unavailable_runtime_is_not_independent(self):
        from ldt_core import runtime as rt
        run = rt.AgentRun(status="unavailable", error="opencode CLI not found")
        with mock.patch.object(rt, "verify_session", return_value={"verified": False}):
            report = rt.independence_report(run, run)
        self.assertEqual(report["independence"], "unavailable")

    def test_model_fallback_is_recorded(self):
        from ldt_core import runtime as rt
        chain = rt.model_candidates("high", ["opencode/nemotron-3.5-super-vl-free",
                                             "opencode/minimax-m3.1-flash-free"])
        self.assertTrue(chain)
        for model in chain:
            self.assertTrue(model.startswith("opencode/"))

    def test_department_lead_uses_a_writable_agent(self):
        from ldt_core import runtime as rt
        self.assertEqual(rt.agent_for_role("department_lead"), "general")
        self.assertFalse(rt.is_read_only_agent(rt.agent_for_role("Department Lead"))
                         if rt.read_only_agents() else True)


class NativeReportPassesTheGate(unittest.TestCase):
    """A real native review must be able to pass."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.impl = TaskContract(
            task_id="impl-001", role="Backend Specialist", goal="Implement",
            architecture_version="v1", milestone_id="M1", base_revision="a" * 40,
            acceptance=["works"], required_checks=["unit-tests"],
            resource_budget={"tokens": 1000, "time_seconds": 60},
            review_assignment="critic-001")
        self.critic = create_critic_contract(
            task_id="critic-001", review_target="impl-001",
            architecture_version="v1", milestone_id="M1", base_revision="a" * 40,
            requirements=["works"], files_in_scope=["src/users.py"],
            resource_budget={"tokens": 1000, "time_seconds": 60})
        from ldt_core.task_contracts import save_contract
        save_contract(self.impl, self.root)
        save_contract(self.critic, self.root)

    def _native_report(self, revision):
        return json.dumps({
            "task_id": "critic-001",
            "reviewed_task_id": "impl-001",
            "reviewed_revision": revision,
            "reviewer": {"session_id": "ses_critic", "agent": "explore", "model": "m",
                         "execution_mode": "native", "verified": True,
                         "read_only_agent": True},
            "coverage": {"requirements_checked": ["works"],
                         "files_inspected": ["src/users.py"],
                         "interfaces_checked": [], "evidence_references": [],
                         "checks_run": [{"name": "unit-tests", "result": "passed",
                                         "evidence": "1 passed"}],
                         "unverified_areas": []},
            "findings": [], "verified_non_findings": ["the change is correct"],
            "confidence": "high", "limitations": [],
            "recommendation": "approve", "summary": "The change is correct.",
        })

    def test_a_native_report_is_accepted(self):
        from ldt_core import pair_execution as pe
        revision = pe._current_revision(self.root)

        critic_run = AgentRun(status="completed", session_id="ses_critic",
                              agent="explore", model="m",
                              output=self._native_report(revision),
                              evidence={"execution_mode": "native"})
        impl_run = AgentRun(status="completed", session_id="ses_impl",
                            agent="general", model="m", output="{}",
                            evidence={"execution_mode": "native"})

        with mock.patch.object(pe, "verify_session", side_effect=lambda sid, cwd=None: {
                "verified": True, "agent": "explore" if sid == "ses_critic" else "general",
                "read_only_agent": sid == "ses_critic"}):
            report, errors = pe._critic_report_from_run(
                self.root, critic_run, self.critic, impl_run, revision)

        self.assertEqual(errors, [])
        self.assertIsNotNone(report)
        self.assertEqual(report.recommendation, "approve")
        self.assertTrue(report.reviewer.read_only_agent)

    def test_a_report_bound_to_another_revision_is_refused(self):
        from ldt_core import pair_execution as pe
        revision = pe._current_revision(self.root)

        critic_run = AgentRun(status="completed", session_id="ses_critic",
                              agent="explore", model="m",
                              output=self._native_report("some-other-revision"),
                              evidence={"execution_mode": "native"})
        impl_run = AgentRun(status="completed", session_id="ses_impl",
                            agent="general", model="m", output="{}",
                            evidence={"execution_mode": "native"})

        with mock.patch.object(pe, "verify_session", return_value={
                "verified": True, "agent": "explore", "read_only_agent": True}):
            report, errors = pe._critic_report_from_run(
                self.root, critic_run, self.critic, impl_run, revision)

        self.assertTrue(any("bound to revision" in e for e in errors))

    def test_a_report_from_a_failed_session_is_refused(self):
        from ldt_core import pair_execution as pe
        failed = AgentRun(status="failed", session_id="ses_critic", agent="explore",
                           model="m", error="provider error")
        impl_run = AgentRun(status="completed", session_id="ses_impl",
                            agent="general", model="m", output="{}",
                            evidence={"execution_mode": "native"})
        report, errors = pe._critic_report_from_run(
            self.root, failed, self.critic, impl_run, "rev")
        self.assertTrue(any("did not complete" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
