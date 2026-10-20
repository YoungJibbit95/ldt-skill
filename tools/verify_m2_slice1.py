#!/usr/bin/env python3
"""Final M2 Slice 1 verification: required checks, package integrity, snapshot.

Run this to produce the evidence bundle for the completion approval.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
VALIDATE = REPO / ".agents/skills/architect-dev-team/scripts/validate.py"
PYTHON = sys.executable
SKILL = REPO / ".agents/skills/architect-dev-team"

results = []


def step(name, cmd, cwd=REPO, expect=0):
    print(f"\n=== {name} ===")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=1800)
    ok = result.returncode == expect
    print(f"exit={result.returncode} expected={expect} -> {'OK' if ok else 'FAIL'}")
    for line in (result.stdout or "").splitlines()[:6]:
        print(f"  | {line}")
    if result.stderr:
        for line in result.stderr.splitlines()[:6]:
            print(f"  ! {line}")
    results.append({"name": name, "exit": result.returncode, "expected": expect, "ok": ok})
    return result


# 1. Full regression suite, discovered exactly as CI does it.
step("Full regression (repository discovery, includes the M1a oracle)",
     [PYTHON, "-B", "-m", "unittest", "discover", "-s", "tests"])

# 2. Package integrity
step("Package integrity", [PYTHON, "-B", str(VALIDATE), "package", str(SKILL)])

# 3. Registry integrity (Schema 1 and Schema 2)
step("Registry Schema 1",
     [PYTHON, "-B", str(VALIDATE), "registry", str(SKILL / "registry/skills.json")])
step("Registry Schema 2 index",
     [PYTHON, "-B", str(VALIDATE), "registry", str(SKILL / "registry/index.json")])

# 4. Runtime capability and the M1a differential oracle
step("M1a differential oracle",
     [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests",
      "-p", "test_core_equivalence.py"])
result = step("Runtime capability", [PYTHON, "-B", str(VALIDATE), "runtime", "detect"])
try:
    info = json.loads(result.stdout)
    print(f"  available={info.get('available')} version={info.get('version')} "
          f"agents={info.get('agents')}")
except Exception:
    pass

# 5. Source snapshot for the completion approval
snapshot = step("Source snapshot",
                [PYTHON, "-B", str(VALIDATE), "snapshot", str(REPO)])
manifest = None
try:
    manifest = json.loads(snapshot.stdout)
except Exception:
    pass
if manifest:
    digest = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    print(f"  files={len(manifest.get('files', []))} head={manifest.get('head_revision')}")
    print(f"  manifest_digest={digest}")

print("\n" + "=" * 60)
failed = [r for r in results if not r["ok"]]
print(f"{len(results) - len(failed)}/{len(results)} verification steps OK")
if failed:
    for r in failed:
        print(f"  FAILED: {r['name']} (exit={r['exit']}, expected={r['expected']})")
    sys.exit(1)
print("All required checks passed.")
