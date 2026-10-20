"""Fast smoke test: real implementer/critic pair on a seeded defect."""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PYTHON = sys.executable
VALIDATE_PY = Path(r"F:\Coding\LittleDevTeamSkill\.agents\skills\architect-dev-team\scripts\validate.py")


def run(args, cwd, label, expect=0):
    cmd = [PYTHON, str(VALIDATE_PY), *[str(a) for a in args]]
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=1800)
    print(f"{'OK ' if result.returncode == expect else '!! '}{label} (exit={result.returncode})")
    for line in (result.stdout or "").splitlines()[:12]:
        print(f"    | {line}")
    if result.stderr:
        for line in result.stderr.splitlines()[:8]:
            print(f"    ! {line}")
    return result


def main():
    root = Path(tempfile.mkdtemp(prefix="ldt_smoke_"))
    try:
        for args in (["init", "-q"], ["config", "user.email", "s@s.invalid"],
                     ["config", "user.name", "S"]):
            subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src" / "__init__.py").write_text("", encoding="utf-8")
        (root / "tests" / "__init__.py").write_text("", encoding="utf-8")
        (root / "src" / "users.py").write_text(
            '"""User registration helpers."""\n\nREGISTRY = {}\n\n\n'
            'def register(email):\n    """Register a user."""\n'
            "    if not email or '@' not in email:\n"
            "        raise ValueError('invalid email')\n"
            "    record = {'email': email}\n"
            "    REGISTRY[email] = record\n    return record\n",
            encoding="utf-8")
        (root / "tests" / "test_users.py").write_text(
            "import pytest\n\nfrom src.users import register\n\n\n"
            "def test_register_returns_record():\n"
            "    assert register('a@example.com')['email'] == 'a@example.com'\n\n\n"
            "def test_register_rejects_invalid_email():\n"
            "    with pytest.raises(ValueError):\n        register('nope')\n",
            encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True,
                       capture_output=True)

        run(["intake", root], root, "intake")
        run(["task-contracts", root, "create-impl",
             "--task-id", "impl-001", "--role", "Backend Specialist",
             "--goal", "Harden user registration against duplicate emails",
             "--arch-version", "v1", "--milestone", "M1",
             "--acceptance", "register('a@example.com') returns a record",
             "--acceptance", "register raises ValueError for a duplicate email",
             "--acceptance", "register raises ValueError for an invalid email",
             "--required-checks", "unit-tests",
             "--review-assignment", "critic-001",
             "--model-profile", "medium"], root, "create impl")
        run(["task-contracts", root, "create-critic",
             "--task-id", "critic-001", "--review-target", "impl-001",
             "--arch-version", "v1", "--milestone", "M1",
             "--model-profile", "high"], root, "create critic")

        run(["pair-exec", root, "run-pair", "--impl-task-id", "impl-001",
             "--critic-task-id", "critic-001"], root, "pair-exec", expect=None)

        ev = root / ".architect-dev-team" / "pair_evidence.json"
        if ev.exists():
            data = json.loads(ev.read_text(encoding="utf-8"))
            for role in ("implementer", "critic"):
                r = data.get(role) or {}
                print(f"  {role}: session={r.get('session_id')} agent={r.get('agent')} "
                      f"model={r.get('model')} status={r.get('status')}")
                print(f"    fallbacks={r.get('evidence', {}).get('model_fallbacks')}")
                out = (r.get("output") or "")[:600]
                print(f"    output: {out}")
            ind = data.get("independence", {})
            print(f"  independence={ind.get('independence')} reasons={ind.get('reasons')}")
            for item in data.get("repair_trail", []):
                print(f"  repair {item}")

        print("--- resulting source ---")
        print((root / "src" / "users.py").read_text(encoding="utf-8"))
        print("--- resulting tests ---")
        print((root / "tests" / "test_users.py").read_text(encoding="utf-8"))

        run(["integration", root, "run"], root, "integration", expect=None)
    finally:
        print(f"cleanup {root}")
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
