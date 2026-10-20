"""The behaviours the re-review found broken and the earlier tests did not cover.

These tests exercise the CLI exit codes, the identity of the stored report,
the order of the digest and the per-round budget. They fail against the
reviewed state.
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

from ldt_core import pair_execution as pe  # noqa: E402
from ldt_core.runtime import AgentRun  # noqa: E402
from ldt_core.task_contracts import (  # noqa: E402
    create_critic_contract, create_implementation_contract, create_lead_contract,
    save_contract,
)


def report_text(task_id="critic-001", reviewed="impl-001", revision="rev-1",
                findings=None, session="ses_critic"):
    data = {
        "task_id": task_id,
        "reviewed_task_id": reviewed,
        "reviewed_revision": revision,
        "reviewer": {"session_id": session, "agent": "explore", "model": "m",
                     "execution_mode": "native", "verified": True,
                     "read_only_agent": True},
        "coverage": {"requirements_checked": ["works"],
                     "files_inspected": ["src/users.py"],
                     "interfaces_checked": [], "evidence_references": [],
                     "checks_run": [{"name": "unit-tests", "result": "passed",
                                     "evidence": "1 passed"}],
                     "unverified_areas": []},
        "findings": findings if findings is not None else [],
        "verified_non_findings": ["looks right"],
        "confidence": "high", "limitations": [],
        "recommendation": "approve", "summary": "The change is correct.",
    }
    return json.dumps(data)


class CliExitCodes(unittest.TestCase):
    """The command exit code reflects the real outcome."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        impl = create_implementation_contract(
            task_id="impl-001", role="Backend Specialist", goal="Implement",
            architecture_version="v1", milestone_id="M1", base_revision="a" * 40,
            acceptance=["works"], required_checks=["unit-tests"],
            resource_budget={"tokens": 1000, "time_seconds": 60},
            review_assignment="critic-001")
        critic = create_critic_contract(
            task_id="critic-001", review_target="impl-001",
            architecture_version="v1", milestone_id="M1", base_revision="a" * 40,
            requirements=["works"], files_in_scope=["src/users.py"],
            resource_budget={"tokens": 1000, "time_seconds": 60})
        save_contract(impl, self.root)
        save_contract(critic, self.root)
        self.verified = {"verified": True, "agent": "explore", "read_only_agent": True}
        # The report must name the revision the tree really has.
        self.revision = pe._current_revision(self.root)

    def _impl_run(self, output="{}"):
        return AgentRun(status="completed", session_id="ses_impl", agent="general",
                        model="m", output=output,
                        evidence={"execution_mode": "native"})

    def test_a_failed_repair_exits_non_zero(self):
        """A repair that did not complete is not a successful pair."""
        impl = self._impl_run()
        finding = [{"severity": "major", "file": "src/users.py", "line": 12,
                    "issue": "case-sensitive duplicate check", "reproduction": "x",
                    "reference": "acceptance"}]
        critic = AgentRun(status="completed", session_id="ses_critic", agent="explore",
                          model="m",
                          output=report_text(revision=self.revision, findings=finding),
                          evidence={"execution_mode": "native"})
        repair = AgentRun(status="failed", session_id="ses_r", agent="general",
                          model="m", error="provider error")

        def fake_run_implementer(root, contract):
            return impl

        def fake_run_critic(root, contract, implementer_result, **kwargs):
            return critic

        with mock.patch.object(pe, "run_implementer", side_effect=fake_run_implementer), \
             mock.patch.object(pe, "run_critic", side_effect=fake_run_critic), \
             mock.patch.object(pe, "dispatch_subagent", return_value=repair), \
             mock.patch.object(pe, "verify_session", return_value=self.verified):
            code = pe.pair_execution_cli(
                self.root, "run-pair", impl_task_id="impl-001",
                critic_task_id="critic-001", max_rounds=2)
        self.assertNotEqual(code, 0, "a failed repair must not exit 0")
        self.assertEqual(code, 6)

    def test_a_rejected_re_review_exits_non_zero(self):
        impl = self._impl_run()
        critic = AgentRun(status="completed", session_id="ses_critic", agent="explore",
                          model="m", output=report_text(),
                          evidence={"execution_mode": "native"})
        repair = AgentRun(status="completed", session_id="ses_r", agent="general",
                          model="m", output="{}",
                          evidence={"execution_mode": "native"})
        # The re-review names the wrong revision and is rejected.
        re_review = AgentRun(status="completed", session_id="ses_c2", agent="explore",
                             model="m", output=report_text(revision="stale"),
                             evidence={"execution_mode": "native"})

        def fake_run_critic(root, contract, implementer_result, **kwargs):
            if contract.task_id == "critic-001":
                return critic
            return re_review

        with mock.patch.object(pe, "run_implementer", return_value=impl), \
             mock.patch.object(pe, "run_critic", side_effect=fake_run_critic), \
             mock.patch.object(pe, "dispatch_subagent", return_value=repair), \
             mock.patch.object(pe, "verify_session", return_value=self.verified):
            code = pe.pair_execution_cli(
                self.root, "run-pair", impl_task_id="impl-001",
                critic_task_id="critic-001", max_rounds=2)
        self.assertNotEqual(code, 0, "a rejected re-review must not exit 0")


class StoredReportIdentity(unittest.TestCase):
    """The stored report is the final one and matches the stored session."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        impl = create_implementation_contract(
            task_id="impl-001", role="Backend Specialist", goal="Implement",
            architecture_version="v1", milestone_id="M1", base_revision="a" * 40,
            acceptance=["works"], required_checks=["unit-tests"],
            resource_budget={"tokens": 1000, "time_seconds": 60},
            review_assignment="critic-001")
        critic = create_critic_contract(
            task_id="critic-001", review_target="impl-001",
            architecture_version="v1", milestone_id="M1", base_revision="a" * 40,
            requirements=["works"], files_in_scope=["src/users.py"],
            resource_budget={"tokens": 1000, "time_seconds": 60})
        save_contract(impl, self.root)
        save_contract(critic, self.root)
        self.verified = {"verified": True, "agent": "explore", "read_only_agent": True}
        # The report must name the revision the tree really has.
        self.revision = pe._current_revision(self.root)

    def test_the_stored_report_belongs_to_the_stored_session(self):
        finding = [{"severity": "major", "file": "src/users.py", "line": 12,
                    "issue": "case-sensitive duplicate check", "reproduction": "x",
                    "reference": "acceptance"}]
        first = AgentRun(status="completed", session_id="ses_critic_first",
                        agent="explore", model="m",
                        output=report_text(findings=finding, session="ses_critic_first",
                                           revision=self.revision),
                        evidence={"execution_mode": "native"})
        impl = AgentRun(status="completed", session_id="ses_impl", agent="general",
                        model="m", output="{}",
                        evidence={"execution_mode": "native"})
        repair = AgentRun(status="completed", session_id="ses_r", agent="general",
                          model="m", output="{}",
                          evidence={"execution_mode": "native"})
        second = AgentRun(status="completed", session_id="ses_critic_final",
                          agent="explore", model="m",
                          output=report_text(session="ses_critic_final",
                                             revision=self.revision),
                          evidence={"execution_mode": "native"})

        def fake_run_critic(root, contract, implementer_result, **kwargs):
            # The first review finds a defect; the re-review does not.
            if not calls.get("reviewed"):
                calls["reviewed"] = True
                return first
            return second

        calls = {}

        with mock.patch.object(pe, "run_implementer", return_value=impl), \
             mock.patch.object(pe, "run_critic", side_effect=fake_run_critic), \
             mock.patch.object(pe, "dispatch_subagent", return_value=repair), \
             mock.patch.object(pe, "verify_session", return_value=self.verified):
            pe.pair_execution_cli(self.root, "run-pair", impl_task_id="impl-001",
                                  critic_task_id="critic-001", max_rounds=2)

        stored = json.loads(
            (self.root / ".architect-dev-team" / "tasks" / "critic-001.json")
            .read_text(encoding="utf-8"))
        self.assertEqual(stored["critic_report"]["reviewer"]["session_id"],
                         stored["session_id"],
                         "the stored report must belong to the stored session")
        self.assertEqual(stored["critic_report"]["findings"], [])


class DigestOrder(unittest.TestCase):
    """The digest is taken after the implementer wrote its files."""

    def test_the_report_must_name_the_post_implementation_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "api.py").write_text("# before\n", encoding="utf-8")
            before = pe._current_revision(root)

            critic = create_critic_contract(
                task_id="critic-001", review_target="impl-001",
                architecture_version="v1", milestone_id="M1", base_revision="a" * 40,
                requirements=["works"], files_in_scope=["src/api.py"],
                resource_budget={"tokens": 1000, "time_seconds": 60})
            impl = AgentRun(status="completed", session_id="ses_impl", agent="general",
                            model="m", output="{}", evidence={"execution_mode": "native"})

            # The implementer changed a file.
            (root / "src" / "api.py").write_text("# after\n", encoding="utf-8")
            after = pe._current_revision(root)
            self.assertNotEqual(before, after)

            verified = {"verified": True, "agent": "explore", "read_only_agent": True}
            for named, accepted in ((after, True), (before, False)):
                run = AgentRun(status="completed", session_id="ses_critic",
                                agent="explore", model="m",
                                output=report_text(revision=named),
                                evidence={"execution_mode": "native"})
                with mock.patch.object(pe, "verify_session", return_value=verified):
                    report, errors = pe._critic_report_from_run(
                        root, run, critic, impl, after)
                if accepted:
                    self.assertEqual(errors, [])
                    self.assertIsNotNone(report)
                else:
                    self.assertTrue(errors, "a report naming an older revision must be refused")


class CorrectionBudgetPerRound(unittest.TestCase):
    """One review round may not consume more corrections than the budget."""

    def test_the_round_is_capped_by_the_budget(self):
        from ldt_core import lead_execution as le
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = create_lead_contract(
                task_id="lead-1", outcome="Deliver",
                architecture_path=".architect-dev-team/architecture.md",
                architecture_sha256="a" * 64, milestone_id="M1",
                base_revision="b" * 40, acceptance=["works"],
                required_checks=["unit-tests"],
                resource_budget={"tokens": 1000, "time_seconds": 60},
                max_specialists=3, max_correction_rounds=2)
            plan = {
                "validates_against_architecture": True, "architecture_conflicts": [],
                "missing_information": [], "risks": [],
                "assignments": [{
                    "task_id": "impl-001", "role": "Backend", "goal": "Implement it",
                    "file_ownership": {"src/api.py": "impl-001"},
                    "acceptance": ["returns 200"], "required_checks": ["unit-tests"],
                    "model_profile": "medium", "review_assignment": "critic-001",
                    "skill_pins": [],
                }],
                "plan_summary": "One specialist.",
            }
            review = {
                "accepted": False,
                "decisions": [
                    {"task_id": "impl-001", "decision": "reject", "reason": "no",
                     "correction": {"goal": "fix", "checks": ["unit-tests"]}},
                    {"task_id": "impl-001", "decision": "reject", "reason": "no",
                     "correction": {"goal": "fix", "checks": ["unit-tests"]}},
                    {"task_id": "impl-001", "decision": "reject", "reason": "no",
                     "correction": {"goal": "fix", "checks": ["unit-tests"]}},
                ],
                "unresolved": [], "escalated": False, "summary": "not accepted.",
            }
            calls = {"n": 0}

            def fake_dispatch(prompt, role, cwd, **kwargs):
                calls["n"] += 1
                if "plan" in kwargs.get("title", ""):
                    return AgentRun(status="completed", session_id="ses_plan",
                                    agent="plan", model="m", output=json.dumps(plan))
                if role == "Backend":
                    return AgentRun(status="completed", session_id=f"ses_s{calls['n']}",
                                    agent="general", model="m",
                                    output=json.dumps({"status": "completed", "changes": [],
                                                      "acceptance_met": False, "findings": [],
                                                      "evidence": {}, "checks": [], "risks": [],
                                                      "unresolved": [], "summary": "partial"}))
                return AgentRun(status="completed", session_id="ses_review",
                                agent="general", model="m", output=json.dumps(review))

            with mock.patch.object(le, "dispatch", side_effect=fake_dispatch):
                result = le.run_department_lead(root, contract,
                                                [{"task_id": "impl-001"}], "# Arch")
            self.assertLessEqual(result.rounds_used, contract.max_correction_rounds)
            self.assertTrue(result.escalated)


if __name__ == "__main__":
    unittest.main()
