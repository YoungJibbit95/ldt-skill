"""Measure where the implementer's tokens actually go.

Runs one real implementer/critic pair and analyses the recorded event stream:
how many tool calls, how many prompt repetitions, how much output per call.
"""
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

PYTHON = sys.executable
VALIDATE = Path(r'F:\Coding\LittleDevTeamSkill\.agents\skills\architect-dev-team\scripts\validate.py')


def build(root: Path):
    for args in (["init", "-q"], ["config", "user.email", "m@m.invalid"],
                 ["config", "user.name", "M"]):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / "src" / "__init__.py").write_text("", encoding="utf-8")
    (root / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (root / "src" / "users.py").write_text(
        '"""Users."""\n\nREGISTRY = {}\n\n\n'
        'def register(email):\n    """Register."""\n'
        "    if not email or '@' not in email:\n"
        "        raise ValueError('invalid email')\n"
        "    record = {'email': email}\n"
        "    REGISTRY[email] = record\n    return record\n", encoding="utf-8")
    (root / "tests" / "test_users.py").write_text(
        "import pytest\n\nfrom src.users import register\n\n\n"
        "def test_ok():\n    assert register('a@example.com')['email'] == 'a@example.com'\n\n\n"
        "def test_invalid():\n    with pytest.raises(ValueError):\n        register('x')\n",
        encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True,
                   capture_output=True)


def main():
    root = Path(tempfile.mkdtemp(prefix="ldt_token_"))
    build(root)
    subprocess.run([PYTHON, "-B", str(VALIDATE), "intake", str(root)],
                   capture_output=True, encoding="utf-8", errors="replace")
    subprocess.run([PYTHON, "-B", str(VALIDATE), "task-contracts", str(root), "create-impl",
                    "--task-id", "impl-001", "--role", "Backend Specialist",
                    "--goal", "Harden user registration against duplicate emails",
                    "--arch-version", "v1", "--milestone", "M1",
                    "--acceptance", "register returns a record",
                    "--acceptance", "register rejects a duplicate email",
                    "--required-checks", "unit-tests",
                    "--review-assignment", "critic-001",
                    "--model-profile", "medium"],
                   capture_output=True, encoding="utf-8", errors="replace")
    subprocess.run([PYTHON, "-B", str(VALIDATE), "task-contracts", str(root), "create-critic",
                    "--task-id", "critic-001", "--review-target", "impl-001",
                    "--arch-version", "v1", "--milestone", "M1",
                    "--model-profile", "high"],
                   capture_output=True, encoding="utf-8", errors="replace")
    result = subprocess.run([PYTHON, "-B", str(VALIDATE), "pair-exec", str(root), "run-pair",
                             "--impl-task-id", "impl-001", "--critic-task-id", "critic-001"],
                            cwd=root, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    print(result.stdout[-1500:])
    if result.stderr:
        print("STDERR:", result.stderr[-800:])

    evidence = root / ".architect-dev-team" / "pair_evidence.json"
    if not evidence.exists():
        print("no evidence")
        return
    data = json.loads(evidence.read_text(encoding="utf-8"))

    for role in ("implementer", "critic"):
        run = data.get(role) or {}
        events = run.get("events") or []
        kinds = Counter()
        tools = Counter()
        texts = 0
        text_chars = 0
        for event in events:
            kinds[event.get("type", "?")] += 1
            part = event.get("part") or {}
            if isinstance(part, dict):
                ptype = part.get("type")
                if ptype == "tool":
                    tool = part.get("tool") or part.get("name") or "?"
                    state = part.get("state") or {}
                    tools[f"{tool}:{state.get('status', '?')}"] += 1
                elif ptype == "text":
                    texts += 1
                    text_chars += len(str(part.get("text") or ""))
        print(f"\n=== {role} ===")
        print(f"  session      : {run.get('session_id')}")
        print(f"  agent/model  : {run.get('agent')} / {run.get('model')}")
        print(f"  status       : {run.get('status')}")
        print(f"  events       : {len(events)}  kinds={dict(kinds)}")
        print(f"  tool calls   : {sum(tools.values())}  {dict(tools)}")
        print(f"  text parts   : {texts}  chars={text_chars}")
        print(f"  output chars : {len(run.get('output') or '')}")
        print(f"  fallbacks    : {run.get('evidence', {}).get('model_fallbacks')}")

    trail = data.get("repair_trail") or []
    print(f"\nrepair rounds: {len(trail)}")
    for item in trail:
        print("   ", {k: v for k, v in item.items() if k in
                     ("round", "group", "outcome", "implementer_session_id", "critic_session_id")})
    print(f"\nproject root: {root}")


if __name__ == "__main__":
    main()
