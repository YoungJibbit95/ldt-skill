#!/usr/bin/env python3
"""Real end-to-end evaluation of the M2 Slice 1 workflow.

Uses an isolated temporary repository, real native OpenCode agents, and a
clearly designated test-authorization fixture. The fixture is NOT a real human
approval and never authorizes work outside the temporary directory.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PYTHON = sys.executable
VALIDATE_PY = Path(r"F:\Coding\LittleDevTeamSkill\.agents\skills\architect-dev-team\scripts\validate.py")
LOG = []


def log(message):
    stamp = time.strftime("%H:%M:%S")
    print(f"[{stamp}] {message}")
    LOG.append(message)


def run(args, cwd, label, expect=0):
    cmd = [PYTHON, str(VALIDATE_PY), *[str(a) for a in args]]
    started = time.time()
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=1800)
    elapsed = time.time() - started
    ok = "OK " if result.returncode == expect else "!! "
    log(f"{ok}{label} (exit={result.returncode}, {elapsed:.1f}s)")
    for line in (result.stdout or "").splitlines():
        log(f"    | {line}")
    if result.stderr:
        for line in result.stderr.splitlines()[:15]:
            log(f"    ! {line}")
    return result


def git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True,
                   capture_output=True, text=True)


def build_fixture(root: Path):
    """Create an isolated project with a real test suite and one seeded defect."""
    git(root, "init", "-q")
    git(root, "config", "user.email", "fixture@test.invalid")
    git(root, "config", "user.name", "LDT Fixture")

    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / "src" / "__init__.py").write_text("", encoding="utf-8")
    (root / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (root / "README.md").write_text(
        "# Task Organizer\n\nSmall web application for organizing tasks.\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "task-organizer"\nversion = "0.1.0"\n', encoding="utf-8")

    # Source with one deliberately seeded defect: the duplicate-email guard is
    # missing, so the acceptance criterion "rejects duplicate email" fails.
    (root / "src" / "users.py").write_text(
        '"""User registration helpers."""\n'
        "\n"
        "REGISTRY = {}\n"
        "\n"
        "\n"
        "def register(email):\n"
        '    """Register a user. Returns the created record."""\n'
        "    if not email or '@' not in email:\n"
        "        raise ValueError('invalid email')\n"
        "    if email in REGISTRY:\n"
        "        raise ValueError('duplicate email')\n"
        "    record = {'email': email}\n"
        "    REGISTRY[email] = record\n"
        "    return record\n",
        encoding="utf-8")

    (root / "tests" / "test_users.py").write_text(
        "import pytest\n"
        "\n"
        "from src.users import register\n"
        "\n"
        "\n"
        "def test_register_returns_record():\n"
        "    record = register('a@example.com')\n"
        "    assert record['email'] == 'a@example.com'\n"
        "\n"
        "\n"
        "def test_register_rejects_invalid_email():\n"
        "    with pytest.raises(ValueError):\n"
        "        register('not-an-email')\n",
        encoding="utf-8")

    git(root, "add", ".")
    git(root, "commit", "-qm", "Fixture: task organizer with seeded defect")
    log(f"Fixture built at {root}")


def main():
    root = Path(tempfile.mkdtemp(prefix="ldt_e2e_"))
    try:
        log("=" * 70)
        log("PHASE 1: Fixture")
        log("=" * 70)
        build_fixture(root)

        log("=" * 70)
        log("PHASE 2: Runtime capability")
        log("=" * 70)
        result = run(["runtime", "detect"], root, "runtime detect", expect=0)
        runtime = json.loads(result.stdout) if result.returncode == 0 else {}
        log(f"    runtime available={runtime.get('available')} "
            f"version={runtime.get('version')}")

        log("=" * 70)
        log("PHASE 3: Intake (vague request -> planning)")
        log("=" * 70)
        run(["intake", root], root, "intake")
        brief = root / ".architect-dev-team" / "brief.md"
        log(f"    brief exists={brief.exists()}")
        if brief.exists():
            text = brief.read_text(encoding="utf-8")
            for marker in ("Open Decisions", "goals.audience", "goals.problem"):
                log(f"    brief contains {marker!r}: {marker in text}")

        log("=" * 70)
        log("PHASE 4: Architecture team decomposition")
        log("=" * 70)
        run(["arch-team", root, "decompose"], root, "arch-team decompose")
        plan_path = root / ".architect-dev-team" / "arch_team_plan.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8")) if plan_path.exists() else {}
        tasks = plan.get("research_tasks", [])
        log(f"    research tasks: {[t['task_id'] for t in tasks]}")

        log("=" * 70)
        log("PHASE 5: Real specialist research (native agents)")
        log("=" * 70)
        for task in tasks:
            result = run(["research", root, task["task_id"], "execute"], root,
                         f"research {task['task_id']}", expect=None)
            log(f"    exit={result.returncode}")

        log("=" * 70)
        log("PHASE 6: Architecture integration")
        log("=" * 70)
        run(["arch-team", root, "integrate"], root, "arch-team integrate")
        arch = root / ".architect-dev-team" / "architecture.md"
        log(f"    architecture exists={arch.exists()}")

        log("=" * 70)
        log("PHASE 7: Task contracts")
        log("=" * 70)
        run(["task-contracts", root, "create-impl",
             "--task-id", "impl-001", "--role", "Backend Specialist",
             "--goal", "Implement and harden user registration",
             "--arch-version", plan.get("architecture_version", "v1"),
             "--milestone", "M1",
             "--acceptance", "register('a@example.com') returns a record",
             "--acceptance", "register rejects a duplicate email",
             "--acceptance", "register rejects an invalid email",
             "--acceptance", "the registered record contains the email",
             "--required-checks", "unit-tests",
             "--review-assignment", "critic-001",
             "--model-profile", "medium"], root, "create impl contract")
        run(["task-contracts", root, "create-critic",
             "--task-id", "critic-001", "--review-target", "impl-001",
             "--arch-version", plan.get("architecture_version", "v1"),
             "--milestone", "M1",
             "--model-profile", "high"], root, "create critic contract")

        log("=" * 70)
        log("PHASE 8: Project overview (start gate)")
        log("=" * 70)
        run(["project-view", root, "generate"], root, "project-view generate")
        view = root / ".architect-dev-team" / "project_view.md"
        if view.exists():
            text = view.read_text(encoding="utf-8")
            for marker in ("Soll ich den ersten beschriebenen Meilenstein",
                           "```mermaid", "impl-001", "critic-001"):
                log(f"    view contains {marker!r}: {marker in text}")

        log("=" * 70)
        log("PHASE 9: Test authorization fixture (NOT a real human approval)")
        log("=" * 70)
        state_dir = root / ".architect-dev-team"
        fixture = state_dir / "TEST_AUTHORIZATION_FIXTURE.json"
        fixture.write_text(json.dumps({
            "kind": "test_authorization_fixture",
            "scope": "isolated temporary project only",
            "grants": ["implementation of M1 in this temporary directory"],
            "note": "Simulation for evaluation. Not a human approval. "
                    "Does not authorize work in any other project.",
            "project_root": str(root),
        }, indent=2), encoding="utf-8")
        log(f"    fixture written: {fixture}")

        log("=" * 70)
        log("PHASE 10: Real implementer/critic pair")
        log("=" * 70)
        result = run(["pair-exec", root, "run-pair",
                      "--impl-task-id", "impl-001",
                      "--critic-task-id", "critic-001"], root, "pair-exec run-pair", expect=None)
        log(f"    exit={result.returncode}")

        evidence = state_dir / "pair_evidence.json"
        if evidence.exists():
            data = json.loads(evidence.read_text(encoding="utf-8"))
            impl = data.get("implementer", {})
            crit = data.get("critic", {})
            ind = data.get("independence", {})
            log(f"    implementer session={impl.get('session_id')} "
                f"agent={impl.get('agent')} model={impl.get('model')} "
                f"status={impl.get('status')}")
            log(f"    critic      session={crit.get('session_id')} "
                f"agent={crit.get('agent')} model={crit.get('model')} "
                f"status={crit.get('status')}")
            log(f"    independence={ind.get('independence')}")
            for reason in ind.get("reasons", []):
                log(f"      reason: {reason}")
            for item in data.get("repair_trail", []):
                log(f"    repair round {item.get('round')}: {item.get('outcome')} "
                    f"impl={item.get('implementer_session_id')} "
                    f"critic={item.get('critic_session_id')}")

        log("=" * 70)
        log("PHASE 11: Integration and final tests")
        log("=" * 70)
        result = run(["integration", root, "run"], root, "integration run", expect=None)
        log(f"    exit={result.returncode}")
        report = state_dir / "integration_report.md"
        if report.exists():
            text = report.read_text(encoding="utf-8")
            for marker in ("Review Independence", "impl-001", "critic-001"):
                log(f"    report contains {marker!r}: {marker in text}")

        log("=" * 70)
        log("PHASE 12: Artifact inventory")
        log("=" * 70)
        for path in sorted(state_dir.rglob("*")):
            if path.is_file():
                log(f"    {path.relative_to(root)} ({path.stat().st_size} bytes)")

        log("=" * 70)
        log("FINAL: session verification via runtime")
        log("=" * 70)
        if evidence.exists():
            data = json.loads(evidence.read_text(encoding="utf-8"))
            for role in ("implementer", "critic"):
                sid = (data.get(role) or {}).get("session_id")
                if sid:
                    result = run(["runtime", "verify", "--session-id", sid,
                                  "--root", root], root,
                                 f"verify {role} session {sid}", expect=None)
                    log(f"    exit={result.returncode}")
    finally:
        log(f"Cleanup: removing {root}")
        shutil.rmtree(root, ignore_errors=True)

    log("=" * 70)
    log("E2E COMPLETE")
    log("=" * 70)


if __name__ == "__main__":
    main()
