#!/usr/bin/env python3
"""Real-agent evaluation of M2 Slice 2 S1 and S2.

Runs a real Department Lead that plans, delegates to a real specialist, and a
real read-only critic that returns a validated CriticReport. Uses the live
OpenCode runtime. Not part of the standard regression suite.
"""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

PYTHON = sys.executable
SCRIPTS = Path(r'F:\Coding\LittleDevTeamSkill\.agents\skills\architect-dev-team\scripts')
sys.path.insert(0, str(SCRIPTS))

from ldt_core.lead_execution import run_department_lead  # noqa: E402
from ldt_core.task_contracts import (  # noqa: E402
    create_critic_contract, create_implementation_contract, create_lead_contract,
    save_contract,
)
from ldt_core.runtime import verify_session  # noqa: E402


ARCHITECTURE = """# Architecture: task registry slice — version v1

## Components
- `src/registry.py` holds the registration store.
- `src/errors.py` holds the error types.

## Interfaces
- `register(email) -> dict` raises `DuplicateEmailError` for a repeated address.

## Contracts
- Addresses are compared case-insensitively after trimming.
- The store is keyed by the canonical address.

## Milestones
| ID | Deliverable | Acceptance | Required checks |
| M1 | registration store | duplicate email rejected | unit-tests |
"""


def build(root: Path):
    for args in (["init", "-q"], ["config", "user.email", "e@e.invalid"],
                 ["config", "user.name", "E"]):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / ".architect-dev-team").mkdir()
    (root / "src" / "__init__.py").write_text("", encoding="utf-8")
    (root / "src" / "errors.py").write_text(
        "class DuplicateEmailError(ValueError):\n    pass\n", encoding="utf-8")
    (root / "src" / "registry.py").write_text(
        '"""Registration store."""\n\nfrom .errors import DuplicateEmailError\n\n'
        "REGISTRY = {}\n\n\n"
        "def register(email):\n"
        '    """Register an address."""\n'
        "    if not email or '@' not in email:\n"
        "        raise ValueError('invalid email')\n"
        "    if email in REGISTRY:\n"
        "        raise DuplicateEmailError('duplicate email')\n"
        "    record = {'email': email}\n"
        "    REGISTRY[email] = record\n"
        "    return record\n", encoding="utf-8")
    (root / "tests" / "test_registry.py").write_text(
        "import pytest\n\nfrom src.registry import register\n\n\n"
        "def test_register_returns_a_record():\n"
        "    assert register('a@example.com')['email'] == 'a@example.com'\n\n\n"
        "def test_register_rejects_a_duplicate():\n"
        "    register('dup@example.com')\n"
        "    with pytest.raises(ValueError):\n"
        "        register('dup@example.com')\n", encoding="utf-8")
    (root / ".architect-dev-team" / "architecture.md").write_text(ARCHITECTURE, encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True, capture_output=True)


def main():
    root = Path(tempfile.mkdtemp(prefix="ldt_s1s2_"))
    build(root)

    # The roster the Master Lead agrees with the department lead. It carries
    # the full specialist definition: the roster is the authority.
    roster = [
        {"task_id": "impl-001", "role": "Backend Specialist",
         "goal": "Implement the canonical registration store with duplicate rejection",
         "acceptance": ["register rejects a duplicate address",
                        "register rejects a case variant of a registered address",
                        "the store is keyed by the canonical address"],
         "required_checks": ["unit-tests"],
         "file_ownership": {"src/registry.py": "impl-001",
                             "src/errors.py": "impl-001",
                             "tests/test_registry.py": "impl-001"},
         "model_profile": "medium", "review_assignment": "critic-001",
         "skill_pins": []},
    ]

    lead = create_lead_contract(
        task_id="lead-backend",
        outcome="Deliver the approved registration store slice",
        architecture_path=".architect-dev-team/architecture.md",
        architecture_sha256=hashlib.sha256(
            (root / ".architect-dev-team" / "architecture.md").read_bytes()
        ).hexdigest(),
        milestone_id="M1-Slice-2",
        base_revision="0" * 40,
        acceptance=["the store rejects a duplicate address"],
        required_checks=["unit-tests"],
        resource_budget={"tokens": 120000, "time_seconds": 900},
        max_specialists=3,
        max_correction_rounds=2,
        specialist_roster=roster,
    )
    save_contract(lead, root)

    print("=== Department Lead run (real native agents) ===")
    result = run_department_lead(root, lead, roster, ARCHITECTURE)

    print(f"status          : {result.status}")
    print(f"accepted        : {result.accepted}")
    print(f"rounds used     : {result.rounds_used}")
    print(f"escalated       : {result.escalated}")
    print(f"summary         : {result.summary[:300]}")
    print(f"plan session    : {result.evidence.get('plan_session_id')}")
    print(f"review sessions : {result.evidence.get('review_sessions')}")
    print(f"missing info    : {result.evidence.get('missing_information')}")
    print(f"risks           : {result.evidence.get('risks')}")
    print(f"unresolved      : {result.unresolved}")

    for specialist in result.specialists:
        print(f"\n  specialist {specialist.get('task_id')}:")
        print(f"    status   : {specialist.get('status')}")
        print(f"    session  : {specialist.get('session_id')}")
        print(f"    agent    : {specialist.get('agent')}")
        print(f"    model    : {specialist.get('model')}")
        print(f"    mode     : {specialist.get('execution_mode')}")
        print(f"    accepted : {specialist.get('acceptance_met')}")
        print(f"    checks   : {specialist.get('checks')}")
        print(f"    summary  : {str(specialist.get('summary'))[:200]}")

    # Verify every session independently.
    print("\n=== session verification ===")
    sessions = []
    if result.evidence.get("plan_session_id"):
        sessions.append(("lead plan", result.evidence["plan_session_id"]))
    for index, sid in enumerate(result.evidence.get("review_sessions", []) or []):
        sessions.append((f"lead review {index + 1}", sid))
    for specialist in result.specialists:
        if specialist.get("session_id"):
            sessions.append((specialist.get("task_id", "specialist"), specialist["session_id"]))
    for label, sid in sessions:
        evidence = verify_session(sid, root)
        print(f"  {label:22s} {sid} verified={evidence.get('verified')} "
              f"agent={evidence.get('agent')} outcome={evidence.get('outcome')} "
              f"read_only={evidence.get('read_only_agent')}")

    # The source the specialists produced.
    print("\n=== resulting source ===")
    for path in sorted((root / "src").glob("*.py")):
        print(f"--- {path.name} ---")
        print(path.read_text(encoding="utf-8"))

    # --- the real pair execution: implementer plus a read-only critic -----
    print("\n=== Pair execution (real native agents) ===")
    impl = create_implementation_contract(
        task_id="impl-001", role="Backend Specialist",
        goal="Implement the canonical registration store with duplicate rejection",
        architecture_version="v1", milestone_id="M1-Slice-2",
        base_revision="0" * 40,
        acceptance=["register rejects a duplicate address",
                    "register rejects a case variant of a registered address"],
        required_checks=["unit-tests"],
        resource_budget={"tokens": 120000, "time_seconds": 900},
        review_assignment="critic-001", model_profile="medium")
    critic = create_critic_contract(
        task_id="critic-001", review_target="impl-001",
        architecture_version="v1", milestone_id="M1-Slice-2",
        base_revision="0" * 40,
        requirements=["register rejects a duplicate address",
                      "register rejects a case variant of a registered address"],
        files_in_scope=["src/registry.py", "src/errors.py", "tests/test_registry.py"],
        required_checks=["unit-tests"],
        resource_budget={"tokens": 60000, "time_seconds": 600},
        model_profile="high")
    save_contract(impl, root)
    save_contract(critic, root)

    pair = subprocess.run(
        [sys.executable, "-B", str(SCRIPTS / "validate.py"), "pair-exec", str(root), "run-pair",
         "--impl-task-id", "impl-001", "--critic-task-id", "critic-001",
         "--max-rounds", "2"],
        cwd=root, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=3600)
    print(pair.stdout[-3000:])
    if pair.stderr:
        print("STDERR:", pair.stderr[-800:])
    print(f"pair exit={pair.returncode}")

    for name in ("impl-001", "critic-001"):
        path = root / ".architect-dev-team" / "tasks" / f"{name}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            print(f"\n  {name}: status={data.get('status')} "
                  f"session={data.get('session_id')} agent={data.get('agent')} "
                  f"model={data.get('model')} mode={data.get('execution_mode')}")
            fallbacks = (data.get("evidence") or {}).get("model_fallbacks") or []
            for attempt in fallbacks:
                print(f"    fallback: {attempt.get('model')} -> "
                      f"{str(attempt.get('error'))[:160]}")
            report = data.get("critic_report")
            if report:
                print(f"    report: task={report.get('task_id')} "
                      f"reviewer_session={report.get('reviewer', {}).get('session_id')} "
                      f"revision={str(report.get('reviewed_revision'))[:16]} "
                      f"confidence={report.get('confidence')} "
                      f"recommendation={report.get('recommendation')}")
                print(f"    coverage: {json.dumps(report.get('coverage', {}))[:400]}")
                print(f"    findings: {json.dumps(report.get('findings', []))[:400]}")
                print(f"    summary: {str(report.get('summary'))[:300]}")
                evidence = verify_session(report.get("reviewer", {}).get("session_id", ""), root)
                print(f"    session verified={evidence.get('verified')} "
                      f"agent={evidence.get('agent')} "
                      f"read_only={evidence.get('read_only_agent')}")

    out = Path(r"F:\Coding\LittleDevTeamSkill\.architect-dev-team")
    out.mkdir(exist_ok=True)
    (out / "s1s2_e2e_result.json").write_text(
        json.dumps(result.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nresult -> {out / 's1s2_e2e_result.json'}")
    print(f"project root: {root}")


if __name__ == "__main__":
    main()
