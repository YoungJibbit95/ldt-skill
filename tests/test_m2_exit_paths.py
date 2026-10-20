"""Tests for the paths the independent re-review found untested.

  * a non-zero agent exit is a failure even with partial output
  * pair-exec exits non-zero when the implementer or the critic run failed
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

from ldt_core import pair_execution as pe  # noqa: E402
from ldt_core import runtime as rt  # noqa: E402
from ldt_core.task_contracts import TaskContract, CriticContract  # noqa: E402


class _Result:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class InvokeExitCode(unittest.TestCase):
    """A crashed agent must not be recorded as a completed run."""

    def test_non_zero_exit_with_text_is_a_failure(self):
        stdout = json.dumps({"type": "text", "sessionID": "ses_x",
                             "part": {"type": "text", "text": "partial"}})
        with mock.patch.object(rt, "_run",
                               return_value=_Result(3, stdout, "boom")):
            run = rt._invoke("opencode", "explore", "model", "p", None, None, 10, None)
        self.assertEqual(run.status, "failed")
        self.assertIn("boom", run.error)

    def test_provider_error_event_is_a_failure(self):
        stdout = json.dumps({"type": "error", "sessionID": "ses_y",
                             "error": {"message": "quota exceeded"}})
        with mock.patch.object(rt, "_run",
                               return_value=_Result(0, stdout, "")):
            run = rt._invoke("opencode", "explore", "model", "p", None, None, 10, None)
        self.assertEqual(run.status, "failed")
        self.assertIn("quota", run.error)

    def test_empty_output_is_a_failure(self):
        with mock.patch.object(rt, "_run", return_value=_Result(0, "", "")):
            run = rt._invoke("opencode", "explore", "model", "p", None, None, 10, None)
        self.assertEqual(run.status, "failed")

    def test_successful_run_is_completed(self):
        stdout = json.dumps({"type": "text", "sessionID": "ses_ok",
                             "part": {"type": "text", "text": "done"}})
        with mock.patch.object(rt, "_run",
                               return_value=_Result(0, stdout, "")):
            run = rt._invoke("opencode", "explore", "model", "p", None, None, 10, None)
        self.assertEqual(run.status, "completed")
        self.assertEqual(run.session_id, "ses_ok")
        self.assertEqual(run.output, "done")


class PairExitCodes(unittest.TestCase):
    """pair-exec must not report success without a completed review."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def _contracts(self):
        impl = TaskContract(task_id="impl-001", role="Backend Specialist", goal="g",
                            architecture_version="v1", milestone_id="M1",
                            base_revision="a" * 40, acceptance=["x"],
                            required_checks=["unit-tests"],
                            resource_budget={"tokens": 1, "time_seconds": 1})
        critic = CriticContract(task_id="critic-001", review_target="impl-001",
                                architecture_version="v1", milestone_id="M1",
                                base_revision="a" * 40)
        pe.save_contract(impl, self.root)
        pe.save_contract(critic, self.root)
        return impl, critic

    def test_failed_implementer_exits_non_zero(self):
        self._contracts()
        failed = rt.AgentRun(status="failed", session_id="ses_i", agent="general",
                             model="m", error="provider error")
        with mock.patch.object(pe, "run_implementer", return_value=failed):
            code = pe.pair_execution_cli(
                self.root, "run-pair", impl_task_id="impl-001",
                critic_task_id="critic-001", max_rounds=2)
        self.assertEqual(code, 3)
        impl = pe.load_contract(self.root, "impl-001")
        self.assertEqual(impl.status, "failed")

    def test_failed_critic_exits_non_zero(self):
        self._contracts()
        ok = rt.AgentRun(status="completed", session_id="ses_i", agent="general",
                         model="m", output="{}")
        failed = rt.AgentRun(status="failed", session_id="ses_c", agent="explore",
                             model="m", error="provider error")
        with mock.patch.object(pe, "run_implementer", return_value=ok), \
             mock.patch.object(pe, "run_critic", return_value=failed), \
             mock.patch.object(rt, "verify_session",
                               return_value={"verified": True, "agent": "explore",
                                             "read_only_agent": True}):
            code = pe.pair_execution_cli(
                self.root, "run-pair", impl_task_id="impl-001",
                critic_task_id="critic-001", max_rounds=2)
        # A critic run that did not complete produces no report, so the pair
        # fails at the report gate.
        self.assertEqual(code, 5)

    def test_unavailable_runtime_exits_with_two(self):
        self._contracts()
        unavailable = rt.AgentRun(status="unavailable", error="opencode CLI not found")
        with mock.patch.object(pe, "run_implementer", return_value=unavailable):
            code = pe.pair_execution_cli(
                self.root, "run-pair", impl_task_id="impl-001",
                critic_task_id="critic-001", max_rounds=2)
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
