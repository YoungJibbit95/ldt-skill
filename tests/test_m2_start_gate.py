"""Start gate enforcement.

The M2 Slice 1 workflow requires an explicit start decision that binds the
exact architecture and task contracts. These tests cover the new approval
kind, its binding, its invalidation and the preserved legacy behaviour.
"""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / ".agents/skills/architect-dev-team/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from ldt_core import approvals as ap  # noqa: E402
from ldt_core.common import Invalid  # noqa: E402
from ldt_core.state import state as validate_state  # noqa: E402


class StartGate(unittest.TestCase):
    """The start approval is a distinct, scope-bound decision."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        (self.root / ".architect-dev-team").mkdir()
        self.arch_bytes = b"# Architecture\n\n## Milestones\n\n| ID | Deliverable |\n| M1 | Test |\n"
        self.arch_path = self.root / ".architect-dev-team" / "architecture.md"
        self.arch_path.write_bytes(self.arch_bytes)
        self.digest = hashlib.sha256(self.arch_bytes).hexdigest()
        self.value = {
            "schema_version": 2, "phase": "INTAKE", "approval_stage": None,
            "profile": "balanced",
            "architecture": {"path": ".architect-dev-team/architecture.md", "sha256": self.digest},
            "milestone": {"id": "M1", "summary": "Test", "acceptance": ["ok"],
                          "required_checks": ["unit-tests"]},
            "approvals": [], "checks": [
                {"name": "unit-tests", "required": True, "status": "not_run",
                 "evidence": "", "waiver": None}],
            "review": None, "completed": [], "open_issues": [], "constraints": [],
            "next_action": "Awaiting start approval",
            "task_contracts": [{"task_id": "impl-001"}],
        }

    def tearDown(self):
        self.temp.cleanup()

    def _decision(self, kind, decision="approved"):
        return {"kind": kind, "decision": decision,
                "scope_sha256": ap.scope(self.value), "review_sha256": None,
                "evidence": "test fixture decision",
                "recorded_at": "2026-10-20T12:00:00+00:00"}

    def _with_architecture(self):
        self.value["approvals"].append(self._decision("architecture"))

    # --- kind acceptance -------------------------------------------------
    def test_start_kind_is_accepted(self):
        self._with_architecture()
        self.value["approvals"].append(self._decision("start"))
        validate_state(self.value, self.root)  # must not raise

    def test_unknown_approval_kind_is_rejected(self):
        self._with_architecture()
        item = self._decision("architecture")
        item["kind"] = "self_approved"
        self.value["approvals"].append(item)
        with self.assertRaisesRegex(Invalid, "invalid approval kind"):
            validate_state(self.value, self.root)

    def test_start_decision_requires_a_null_review_digest(self):
        self._with_architecture()
        item = self._decision("start")
        item["review_sha256"] = "a" * 64
        self.value["approvals"].append(item)
        with self.assertRaisesRegex(Invalid, "null review hash"):
            validate_state(self.value, self.root)

    # --- gate behaviour --------------------------------------------------
    def test_implement_gate_requires_start_for_m2_state(self):
        self._with_architecture()
        self.value["phase"] = "IMPLEMENTATION"
        self.value["approval_stage"] = None
        with self.assertRaisesRegex(Invalid, "missing start approval"):
            validate_state(self.value, self.root, "implement")

    def test_implement_gate_passes_with_start_approval(self):
        self._with_architecture()
        self.value["approvals"].append(self._decision("start"))
        self.value["phase"] = "IMPLEMENTATION"
        self.value["approval_stage"] = None
        validate_state(self.value, self.root, "implement")  # must not raise

    def test_legacy_state_without_task_contracts_keeps_legacy_behaviour(self):
        """A pre-M2 state needs no start decision. Legacy records keep working."""
        self.value.pop("task_contracts")
        self._with_architecture()
        self.value["phase"] = "IMPLEMENTATION"
        self.value["approval_stage"] = None
        validate_state(self.value, self.root, "implement")  # must not raise

    # --- binding ---------------------------------------------------------
    def test_start_approval_is_invalidated_by_a_scope_change(self):
        """A changed scope refuses the gate. Architecture is checked first, and
        both approvals share one scope fingerprint, so the refusal is equivalent.
        """
        self._with_architecture()
        self.value["approvals"].append(self._decision("start"))
        self.value["milestone"]["summary"] = "Changed"
        with self.assertRaisesRegex(Invalid, r"stale (start|architecture) approval scope"):
            validate_state(self.value, self.root, "implement")

    def test_start_approval_is_invalidated_by_a_profile_change(self):
        self._with_architecture()
        self.value["approvals"].append(self._decision("start"))
        self.value["profile"] = "rigorous"
        with self.assertRaisesRegex(Invalid, r"stale (start|architecture) approval scope"):
            validate_state(self.value, self.root, "implement")

    def test_start_alone_is_insufficient_when_only_the_architecture_is_stale(self):
        """A start decision cannot rescue a stale architecture approval."""
        self._with_architecture()
        self.value["approvals"].append(self._decision("start"))
        # Re-bind only the start decision to the new scope, leaving the
        # architecture approval stale.
        self.value["milestone"]["summary"] = "Changed"
        self.value["approvals"][1]["scope_sha256"] = ap.scope(self.value)
        with self.assertRaisesRegex(Invalid, "stale architecture approval scope"):
            validate_state(self.value, self.root, "implement")

    def test_rejected_start_supersedes_an_earlier_approval(self):
        self._with_architecture()
        self.value["approvals"].append(self._decision("start"))
        self.value["approvals"].append(self._decision("start", decision="rejected"))
        self.value["phase"] = "IMPLEMENTATION"
        self.value["approval_stage"] = None
        with self.assertRaisesRegex(Invalid, "latest start decision is rejected"):
            validate_state(self.value, self.root, "implement")

    def test_start_requires_an_approved_architecture(self):
        """A start decision without an architecture approval is not enough."""
        self.value["approvals"].append(self._decision("start"))
        self.value["phase"] = "IMPLEMENTATION"
        self.value["approval_stage"] = None
        with self.assertRaisesRegex(Invalid, "missing architecture approval"):
            validate_state(self.value, self.root, "implement")

    def test_start_does_not_weaken_the_iteration_gate(self):
        """A start approval never satisfies the iteration gate."""
        self._with_architecture()
        self.value["approvals"].append(self._decision("start"))
        self.value["phase"] = "NEXT_ITERATION"
        self.value["approval_stage"] = None
        with self.assertRaises(Invalid):
            validate_state(self.value, self.root, "advance")

    def test_start_scope_uses_the_same_fingerprint_as_architecture(self):
        """No second state machine: start and architecture share one scope."""
        self._with_architecture()
        start = self._decision("start")
        self.assertEqual(start["scope_sha256"], ap.scope(self.value))


if __name__ == "__main__":
    unittest.main()
