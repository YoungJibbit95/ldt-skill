"""
Task Contracts: Creation, validation, serialization for implementation and critic tasks.
Python 3.10+, stdlib only.
"""
from __future__ import annotations
import json
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

from .common import Invalid


@dataclass
class TaskContract:
    task_id: str
    role: str = ""
    goal: str = ""
    architecture_version: str = ""
    milestone_id: str = ""
    base_revision: str = ""
    contract_refs: list[str] = field(default_factory=list)
    input_paths: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    allowed_actions: list[str] = field(default_factory=list)
    file_ownership: dict[str, str] = field(default_factory=dict)
    acceptance: list[str] = field(default_factory=list)
    required_checks: list[str] = field(default_factory=list)
    skill_pins: list[str] = field(default_factory=list)
    model_profile: str = "medium"
    resource_budget: dict[str, Any] = field(default_factory=dict)
    review_assignment: Optional[str] = None
    escalation: list[str] = field(default_factory=list)

    # Result fields (populated at completion)
    status: str = "created"
    changes: list[dict[str, str]] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    evidence: dict[str, str] = field(default_factory=dict)
    checks: list[dict[str, Any]] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    review_notes: str = ""

    # Runtime evidence (real native agent execution)
    session_id: Optional[str] = None
    agent: Optional[str] = None
    model: Optional[str] = None
    execution_mode: Optional[str] = None  # native | fixture

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    @staticmethod
    def from_json(data: str) -> TaskContract:
        return TaskContract(**json.loads(data))

    def to_markdown(self, template_path: Path) -> str:
        template = template_path.read_text(encoding="utf-8")
        def safe_str(v):
            return str(v) if v is not None else ""
        replacements = {
            "<task_id>": safe_str(self.task_id),
            "<role>": safe_str(self.role),
            "<single concrete outcome>": safe_str(self.goal),
            "<version>": safe_str(self.architecture_version),
            "<milestone_id>": safe_str(self.milestone_id),
            "<git sha>": safe_str(self.base_revision),
            "<contract-id-1>": self._fmt_list(self.contract_refs),
            "<path/glob>": self._fmt_list(self.input_paths),
            "<task-id-1>": self._fmt_list(self.dependencies),
            "<path/**>": self._fmt_list(self.allowed_actions),
            "<path> | <task_id>": self._fmt_ownership(),
            "<observable criterion 1>": self._fmt_list(self.acceptance),
            "<check-name-1>": self._fmt_list(self.required_checks),
            "<skill-id>@<revision>": self._fmt_list(self.skill_pins),
            "<low | medium | high>": safe_str(self.model_profile),
            "<limit>": str(self.resource_budget.get("tokens", "")),
            "<seconds>": str(self.resource_budget.get("time_seconds", "")),
            "<max parallel>": str(self.resource_budget.get("concurrency", "")),
            "<critic-task-id>": safe_str(self.review_assignment),
            "<created | modified | deleted>": self._fmt_changes(),
            "<hash>": "",
            "<finding 1>": self._fmt_list(self.findings),
            "<check>: <command>: <outcome>": self._fmt_evidence(),
            "<check> | <passed|failed|waived> | <evidence>": self._fmt_checks(),
            "<risk>": self._fmt_list(self.risks),
            "<item>": self._fmt_list(self.unresolved),
            "<notes for critic>": safe_str(self.review_notes),
        }
        result = template
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)
        return result

    def _fmt_list(self, items: list) -> str:
        return "\n".join(f"- {item}" for item in items) if items else "(none)"

    def _fmt_ownership(self) -> str:
        if not self.file_ownership:
            return "| (none) | |\n| --- | --- |"
        return "\n".join(f"| {path} | {owner} |" for path, owner in self.file_ownership.items())

    def _fmt_changes(self) -> str:
        if not self.changes:
            return "| (none) | | |\n| --- | --- | --- |"
        return "\n".join(f"| {c.get('path', '')} | {c.get('action', '')} | {c.get('sha256', '')} |" for c in self.changes)

    def _fmt_evidence(self) -> str:
        if not self.evidence:
            return "(none)"
        return "\n".join(f"- {k}: {v}" for k, v in self.evidence.items())

    def _fmt_checks(self) -> str:
        if not self.checks:
            return "| (none) | | |\n| --- | --- | --- |"
        return "\n".join(f"| {c.get('name', '')} | {c.get('status', '')} | {c.get('evidence', '')} |" for c in self.checks)


@dataclass
class CriticContract(TaskContract):
    """Extended contract for independent critic."""
    review_target: str = ""
    # Independence is proven by runtime evidence, never declared up front.
    independence: str = "unavailable"  # independent, self, unavailable
    review_criteria: list[str] = field(default_factory=list)
    prohibited_actions: list[str] = field(default_factory=list)
    evidence_requirements: list[str] = field(default_factory=list)
    # The requirements the critic must cover and the files it may inspect.
    requirements: list[str] = field(default_factory=list)
    files_in_scope: list[str] = field(default_factory=list)
    # The validated report from the review run.
    critic_report: Optional[dict[str, Any]] = None

    def __post_init__(self):
        self.role = "Independent Critic"
        if not self.prohibited_actions:
            self.prohibited_actions = ["write:src/**", "write:production/**"]
        if not self.evidence_requirements:
            self.evidence_requirements = ["file:line references", "reproduction steps", "spec references", "test cases"]


@dataclass
class LeadContract(TaskContract):
    """Contract for a Department Lead.

    The lead coordinates a bounded set of specialists. It does not approve,
    integrate or expand the scope; the Master Lead keeps that authority.
    """
    department: str = ""
    outcome: str = ""
    architecture_path: str = ""
    architecture_sha256: str = ""
    specialist_roster: list[dict[str, Any]] = field(default_factory=list)
    max_specialists: int = 3
    max_correction_rounds: int = 2
    # The handoff the lead produced.
    lead_result: Optional[dict[str, Any]] = None

    def __post_init__(self):
        if not self.role:
            self.role = "Department Lead"


@dataclass
class LeadResult:
    """The validated department handoff returned to the Master Lead."""
    lead_task_id: str = ""
    status: str = "completed"
    accepted: bool = False
    specialists: list[dict[str, Any]] = field(default_factory=list)
    corrections: list[dict[str, Any]] = field(default_factory=list)
    rounds_used: int = 0
    unresolved: list[str] = field(default_factory=list)
    escalated: bool = False
    summary: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(value: Any) -> "LeadResult":
        if not isinstance(value, dict):
            raise Invalid("lead result must be an object")
        return LeadResult(
            lead_task_id=str(value.get("lead_task_id", "") or ""),
            status=str(value.get("status", "") or ""),
            accepted=bool(value.get("accepted", False)),
            specialists=value.get("specialists") or [],
            corrections=value.get("corrections") or [],
            rounds_used=int(value.get("rounds_used", 0) or 0),
            unresolved=value.get("unresolved") or [],
            escalated=bool(value.get("escalated", False)),
            summary=str(value.get("summary", "") or ""),
            evidence=value.get("evidence") or {},
        )


def create_implementation_contract(
    task_id: str,
    role: str,
    goal: str,
    architecture_version: str,
    milestone_id: str,
    base_revision: str,
    **kwargs
) -> TaskContract:
    """Factory for implementation contracts."""
    return TaskContract(
        task_id=task_id,
        role=role,
        goal=goal,
        architecture_version=architecture_version,
        milestone_id=milestone_id,
        base_revision=base_revision,
        **kwargs
    )


def create_critic_contract(
    task_id: str,
    review_target: str,
    architecture_version: str,
    milestone_id: str,
    base_revision: str,
    **kwargs
) -> CriticContract:
    """Factory for critic contracts."""
    kwargs.setdefault("resource_budget", {"tokens": 30000, "time_seconds": 300})
    return CriticContract(
        task_id=task_id,
        review_target=review_target,
        architecture_version=architecture_version,
        milestone_id=milestone_id,
        base_revision=base_revision,
        goal=f"Verify {review_target} against requirements and find defects",
        **kwargs
    )


def create_lead_contract(
    task_id: str,
    outcome: str,
    architecture_path: str,
    architecture_sha256: str,
    milestone_id: str,
    base_revision: str,
    **kwargs
) -> LeadContract:
    """Factory for department lead contracts."""
    return LeadContract(
        task_id=task_id,
        role="Department Lead",
        outcome=outcome,
        architecture_path=architecture_path,
        architecture_sha256=architecture_sha256,
        milestone_id=milestone_id,
        base_revision=base_revision,
        goal=outcome,
        **kwargs
    )


def validate_contract(contract: TaskContract, milestone_required_checks: list[str], approved_skills: list[str]) -> list[str]:
    """Validate contract against milestone policy and approved skills. Returns list of errors."""
    errors = []

    # Required fields
    required = ["task_id", "role", "goal", "architecture_version", "milestone_id", "base_revision"]
    for field_name in required:
        if not getattr(contract, field_name):
            errors.append(f"Missing required field: {field_name}")

    # required_checks subset of milestone
    for check in contract.required_checks:
        if check not in milestone_required_checks:
            errors.append(f"Check '{check}' not in milestone.required_checks: {milestone_required_checks}")

    # skill_pins reference approved skills
    for pin in contract.skill_pins:
        skill_id = pin.split("@")[0]
        if skill_id not in approved_skills:
            errors.append(f"Skill '{skill_id}' not in approved skills: {approved_skills}")

    # file_ownership no overlaps (would need all active contracts)
    # model_profile valid
    if contract.model_profile not in ("low", "medium", "high"):
        errors.append(f"Invalid model_profile: {contract.model_profile}")

    # resource_budget has tokens and time
    if "tokens" not in contract.resource_budget:
        errors.append("resource_budget missing 'tokens'")
    if "time_seconds" not in contract.resource_budget:
        errors.append("resource_budget missing 'time_seconds'")

    # Critic-specific
    if isinstance(contract, CriticContract):
        if contract.independence not in ("independent", "self", "unavailable"):
            errors.append(f"Invalid independence: {contract.independence}")
        if not contract.review_target:
            errors.append("Critic contract missing review_target")
        if not contract.requirements:
            errors.append("Critic contract missing the requirements to cover")
    if isinstance(contract, LeadContract):
        if not contract.outcome:
            errors.append("Lead contract missing the outcome")
        if not contract.architecture_path:
            errors.append("Lead contract missing the architecture reference")
        if contract.max_specialists < 1:
            errors.append("Lead contract must allow at least one specialist")
        if contract.max_correction_rounds < 0:
            errors.append("Lead contract correction rounds must not be negative")

    return errors


def safe_task_id(task_id: str) -> str:
    """Validate a task id as a single safe file name.

    The id is used as a file name. A traversal or separator in it would
    write outside the task directory, so it is rejected here.
    """
    text = str(task_id or "").strip()
    if not text or text in {".", ".."}:
        raise Invalid(f"invalid task id: {task_id!r}")
    if any(char in text for char in ("/", "\\", ":", "*", "?", '"', "<", ">", "|", "\x00")):
        raise Invalid(f"invalid task id: {task_id!r}")
    if text.startswith("."):
        raise Invalid(f"invalid task id: {task_id!r}")
    return text


def record_contract_in_state(root: Path, task_id: str) -> None:
    """Record a created contract in the project state.

    The state list is what the start gate binds to. Recording it here means
    the gate reflects the contracts that actually exist.
    """
    state_path = root / ".architect-dev-team" / "state.json"
    if not state_path.exists():
        return
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return
    if not isinstance(state, dict):
        return
    contracts = state.get("task_contracts")
    if not isinstance(contracts, list):
        contracts = []
    if task_id not in contracts:
        contracts.append(task_id)
    state["task_contracts"] = contracts
    try:
        state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def save_contract(contract: TaskContract, root: Path) -> Path:
    """Save contract to .architect-dev-team/tasks/<task_id>.json and .md"""
    contract.task_id = safe_task_id(contract.task_id)
    state_dir = root / ".architect-dev-team"
    state_dir.mkdir(exist_ok=True)
    tasks_dir = state_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    json_path = tasks_dir / f"{contract.task_id}.json"
    json_path.write_text(contract.to_json(), encoding="utf-8")
    template_path = Path(__file__).parent.parent.parent / "assets" / "task.template.md"
    md_path = tasks_dir / f"{contract.task_id}.md"
    md_path.write_text(contract.to_markdown(template_path), encoding="utf-8")
    return json_path


def load_contract(root: Path, task_id: str) -> TaskContract:
    json_path = root / ".architect-dev-team" / "tasks" / f"{task_id}.json"
    if not json_path.exists():
        raise Invalid(f"Task contract not found: {json_path}")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    # The contract kind decides the class. A lead contract is recognised by
    # its own fields, a critic contract by its review target.
    if "outcome" in data or "specialist_roster" in data:
        return LeadContract(**data)
    if "review_target" in data:
        return CriticContract(**data)
    return TaskContract(**data)


def list_contracts(root: Path) -> list[TaskContract]:
    tasks_dir = root / ".architect-dev-team" / "tasks"
    if not tasks_dir.exists():
        return []
    contracts = []
    for json_path in tasks_dir.glob("*.json"):
        try:
            contracts.append(TaskContract.from_json(json_path.read_text(encoding="utf-8")))
        except Exception:
            pass
    return contracts


def get_git_revision(root: Path) -> str:
    """Get current HEAD revision."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


# CLI for validate.py
def task_contracts_cli(root: Path, command: str, **kwargs) -> int:
    try:
        if command == "create-impl":
            contract = create_implementation_contract(
                task_id=kwargs["task_id"],
                role=kwargs["role"],
                goal=kwargs["goal"],
                architecture_version=kwargs["arch_version"],
                milestone_id=kwargs["milestone"],
                base_revision=get_git_revision(root),
                contract_refs=kwargs.get("contract_refs") or [],
                input_paths=kwargs.get("input_paths") or [],
                dependencies=kwargs.get("dependencies") or [],
                allowed_actions=kwargs.get("allowed_actions") or [],
                file_ownership=kwargs.get("file_ownership") or {},
                acceptance=kwargs.get("acceptance") or [],
                required_checks=kwargs.get("required_checks") or [],
                skill_pins=kwargs.get("skill_pins") or [],
                model_profile=kwargs.get("model_profile") or "medium",
                resource_budget=kwargs.get("resource_budget") or {"tokens": 50000, "time_seconds": 300},
                review_assignment=kwargs.get("review_assignment"),
                escalation=kwargs.get("escalation") or ["scope_change", "missing_decision", "security_risk"],
            )
            save_contract(contract, root)
            record_contract_in_state(root, contract.task_id)
            print(f"Implementation contract created: {contract.task_id}")
            return 0
        elif command == "create-critic":
            contract = create_critic_contract(
                task_id=kwargs["task_id"],
                review_target=kwargs["review_target"],
                architecture_version=kwargs["arch_version"],
                milestone_id=kwargs["milestone"],
                base_revision=get_git_revision(root),
                allowed_actions=kwargs.get("allowed_actions") or ["read:src/**", "read:tests/**", "exec:pytest"],
                required_checks=kwargs.get("required_checks") or ["pair-review"],
                model_profile=kwargs.get("model_profile") or "medium",
                resource_budget=kwargs.get("resource_budget") or {"tokens": 30000, "time_seconds": 180},
            )
            save_contract(contract, root)
            record_contract_in_state(root, contract.task_id)
            print(f"Critic contract created: {contract.task_id}")
            return 0
        elif command == "validate":
            contract = load_contract(root, kwargs["task_id"])
            # Load milestone required_checks from state
            state_path = root / ".architect-dev-team" / "state.json"
            milestone_checks = []
            approved_skills = []
            if state_path.exists():
                state = json.loads(state_path.read_text(encoding="utf-8"))
                if state.get("milestone"):
                    milestone_checks = state["milestone"].get("required_checks", [])
                # The approved skills are the ones the project recorded. The
                # registry offers skills, the project approves them.
                approved = state.get("approved_skills")
                if isinstance(approved, list):
                    approved_skills = [str(item) for item in approved if item]
            errors = validate_contract(contract, milestone_checks, approved_skills)
            if errors:
                for e in errors:
                    print(f"ERROR: {e}")
                return 1
            print(f"Contract {contract.task_id} valid")
            return 0
        elif command == "list":
            contracts = list_contracts(root)
            for c in contracts:
                print(f"{c.task_id}: {c.role} - {c.status}")
            return 0
        else:
            print(f"Unknown command: {command}", file=sys.stderr)
            return 1
    except Invalid as e:
        print(f"INVALID: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"INVALID: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Task contract management")
    parser.add_argument("root", type=Path)
    parser.add_argument("command", choices=["create-impl", "create-critic", "validate", "list"])
    parser.add_argument("--task-id", type=str)
    parser.add_argument("--role", type=str)
    parser.add_argument("--goal", type=str)
    parser.add_argument("--arch-version", type=str)
    parser.add_argument("--milestone", type=str)
    parser.add_argument("--review-target", type=str)
    parser.add_argument("--contract-refs", type=str, nargs="*")
    parser.add_argument("--input-paths", type=str, nargs="*")
    parser.add_argument("--dependencies", type=str, nargs="*")
    parser.add_argument("--allowed-actions", type=str, nargs="*")
    parser.add_argument("--acceptance", type=str, nargs="*")
    parser.add_argument("--required-checks", type=str, nargs="*")
    parser.add_argument("--skill-pins", type=str, nargs="*")
    parser.add_argument("--model-profile", type=str)
    parser.add_argument("--review-assignment", type=str)
    args = parser.parse_args()
    sys.exit(task_contracts_cli(args.root, args.command, **vars(args)))