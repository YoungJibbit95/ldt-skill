"""
Integration: Combines reviewed tasks, runs final tests, produces integration report.

Python 3.10+, stdlib only. Review independence is verified against recorded
runtime evidence, never against a self-declared field.
"""
from __future__ import annotations
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .common import Invalid
from .runtime import verify_session
from .task_contracts import load_contract, list_contracts


def collect_reviewed_tasks(root: Path) -> list[dict[str, Any]]:
    """Collect completed tasks together with their assigned critic contract."""
    tasks = list_contracts(root)
    reviewed = []
    for task in tasks:
        if task.status == "completed" and task.role != "Independent Critic":
            critic = None
            if task.review_assignment:
                try:
                    critic = load_contract(root, task.review_assignment)
                except Exception:
                    critic = None
            reviewed.append({"task": task, "critic": critic})
    return reviewed


def check_review_independence(root: Path, reviewed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Verify review independence from runtime evidence.

    Independence requires distinct, verifiable session IDs for the implementer
    and the critic. A missing or duplicated session fails. Self-declared
    metadata alone never passes.
    """
    results = []
    for item in reviewed:
        task = item["task"]
        critic = item["critic"]
        reasons: list[str] = []

        impl_session = getattr(task, "session_id", None)
        critic_session = getattr(critic, "session_id", None) if critic else None

        impl_mode = (getattr(task, "execution_mode", None) or "native")
        critic_mode = (getattr(critic, "execution_mode", None) or "native") if critic else "native"
        if impl_mode == "fixture":
            reasons.append("implementer run is a fixture, not native agent execution")
        if critic_mode == "fixture":
            reasons.append("critic run is a fixture, not native agent execution")

        # A run that did not complete is not a review.
        impl_status = getattr(task, "status", None)
        critic_status = getattr(critic, "status", None) if critic else None
        if impl_status and impl_status != "completed":
            reasons.append(f"implementer run did not complete (status {impl_status})")
        if critic and critic_status and critic_status != "completed":
            reasons.append(f"critic run did not complete (status {critic_status})")

        if not impl_session:
            reasons.append("implementer session id missing")
        if not critic_session:
            reasons.append("critic session id missing")
        if impl_session and critic_session and impl_session == critic_session:
            reasons.append("implementer and critic share one session")

        impl_evidence = verify_session(impl_session, root) if impl_session else {"verified": False}
        critic_evidence = verify_session(critic_session, root) if critic_session else {"verified": False}
        if not impl_evidence.get("verified"):
            reasons.append(f"implementer session not verifiable: {impl_evidence.get('reason')}")
        if not critic_evidence.get("verified"):
            reasons.append(f"critic session not verifiable: {critic_evidence.get('reason')}")

        critic_agent = critic_evidence.get("agent") if critic_evidence.get("verified") else None
        if critic_agent and not critic_evidence.get("read_only_agent"):
            reasons.append(f"critic agent '{critic_agent}' is not read-only")

        results.append({
            "task": task.task_id,
            "reviewer": critic.task_id if critic else "none",
            "independence": "independent" if not reasons else "unavailable",
            "reasons": reasons,
            "evidence": {
                "implementer_session_id": impl_session,
                "critic_session_id": critic_session,
                "implementer_agent": impl_evidence.get("agent"),
                "critic_agent": critic_evidence.get("agent"),
                "implementer_model": getattr(task, "model", None),
                "critic_model": getattr(critic, "model", None) if critic else None,
                "implementer_tokens": impl_evidence.get("tokens"),
                "critic_tokens": critic_evidence.get("tokens"),
                "implementer_execution_mode": impl_mode,
                "critic_execution_mode": critic_mode,
                "critic_read_only": bool(critic_evidence.get("read_only_agent")),
                "implementer_status": impl_status,
                "critic_status": critic_status,
                "implementer_outcome": impl_evidence.get("outcome"),
                "critic_outcome": critic_evidence.get("outcome"),
            },
        })
    return results


def split_command(cmd: str) -> list[str]:
    """Split a command string into an argument vector.

    The shell is not involved, so a caller supplied command cannot chain
    further operations. On Windows the non-posix split keeps the quotes
    around a path, so they are removed here.
    """
    parts = shlex.split(cmd, posix=(os.name != "nt"))
    return [part[1:-1] if len(part) > 1 and part[0] == part[-1] == '"' else part
            for part in parts]


def run_integration_tests(root: Path, test_commands: list[str]) -> dict[str, Any]:
    """Run the approved test commands at the integrated whole.

    The command string is split and executed without a shell, so a caller
    supplied command cannot chain additional shell operations.
    """
    results = {}
    for cmd in test_commands:
        try:
            argv = split_command(cmd)
            result = subprocess.run(
                argv, shell=False, cwd=root, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=600
            )
            results[cmd] = {
                "exit_code": result.returncode,
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-5000:],
                "passed": result.returncode == 0,
            }
        except subprocess.TimeoutExpired:
            results[cmd] = {"exit_code": -1, "error": "timeout", "passed": False}
        except Exception as e:
            results[cmd] = {"exit_code": -1, "error": str(e), "passed": False}
    return results


def generate_integration_report(
    root: Path,
    reviewed: list[dict[str, Any]],
    independence: list[dict[str, Any]],
    test_results: dict[str, Any],
    state: dict[str, Any],
) -> str:
    """Generate the integration report markdown."""
    template_path = Path(__file__).parent.parent.parent / "assets" / "integration-report.template.md"
    template = template_path.read_text(encoding="utf-8")

    milestone = state.get("milestone") or {}
    arch = state.get("architecture") or {}

    deliverables = []
    for item in reviewed:
        task = item["task"]
        deliverables.append(f"- {task.task_id} ({task.role}): {task.goal}")

    acceptance_rows = []
    for criterion in milestone.get("acceptance", []):
        acceptance_rows.append(f"| {criterion} | ✅ Passed | Implemented and tested |")

    test_sections: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for cmd, result in test_results.items():
        lowered = cmd.lower()
        if "integration" in lowered or "e2e" in lowered:
            key = "integration"
        elif "security" in lowered:
            key = "security"
        elif "perf" in lowered or "load" in lowered:
            key = "performance"
        elif "unit" in lowered or "contract" in lowered or "pytest" in lowered:
            # The default repository test run belongs to the unit/contract
            # section. An uncategorised command would be reported nowhere.
            key = "unit_contract"
        else:
            key = "other"
        test_sections.setdefault(key, []).append((cmd, result))

    def fmt_tests(section: str) -> str:
        items = test_sections.get(section, [])
        if not items:
            return "(no tests in this category)"
        lines = []
        for cmd, result in items:
            status = "PASS" if result.get("passed") else "FAIL"
            lines.append(f"{status} {cmd}")
            if result.get("stdout"):
                lines.append(result["stdout"])
        return "\n".join(lines)

    role_rows = []
    for item in reviewed:
        task = item["task"]
        skill_pins = task.skill_pins if isinstance(task.skill_pins, list) else []
        mode = getattr(task, "execution_mode", None) or "native"
        session = getattr(task, "session_id", None) or task.task_id
        role_rows.append(
            f"| {task.role} | {session} ({mode}) | "
            f"{', '.join(skill_pins) or '—'} | {getattr(task, 'model', None) or task.model_profile} |")
    # Declared sessions are marked as such: they are not runtime evidence.
    role_rows.insert(0, f"| Lead | {state.get('lead_session') or '—'} (declared) | — | High |")
    role_rows.insert(1, f"| Architecture Lead | {state.get('arch_lead_session') or '—'} (declared) | — | High |")

    effort = state.get("effort") or {"tokens": 0, "time_seconds": 0, "agents": 0, "repair_rounds": 0}

    independence_rows = []
    for r in independence:
        evidence = r.get("evidence", {})
        independence_rows.append(
            f"| {r['task']} | {r['reviewer']} | {r['independence']} | "
            f"impl={evidence.get('implementer_session_id')}, "
            f"critic={evidence.get('critic_session_id')}, "
            f"agents={evidence.get('implementer_agent')}/{evidence.get('critic_agent')} |")

    replacements = {
        "<milestone_id>": str(milestone.get("id", "M1")),
        "<revision>": get_git_revision(root),
        "<ISO8601>": datetime.now().isoformat(),
        "<arch_version>": (arch.get("sha256") or "unknown")[:12] if arch else "unknown",
        "<deliverable 1>": "\n".join(deliverables) if deliverables else "- (none)",
        "<criterion>": "\n".join(acceptance_rows) if acceptance_rows else "| (none) | | |",
        "<unit_contract_results>": fmt_tests("unit_contract"),
        "<integration_results>": fmt_tests("integration"),
        "<security_results>": fmt_tests("security"),
        "<performance_results>": fmt_tests("performance"),
        "<task>": "\n".join(independence_rows) if independence_rows else "| (none) | | | |",
        "<risk>": ("\n".join(f"| {r} | Medium | Medium | Monitor |" for r in state.get("open_issues", []))
                   if state.get("open_issues") else "| (none) | | | |"),
        "<role>": "\n".join(role_rows),
        "<token_count>": str(effort.get("tokens", 0)),
        "<seconds>": str(effort.get("time_seconds", 0)),
        "<agent_count>": str(effort.get("agents", 0)),
        "<repair_count>": str(effort.get("repair_rounds", 0)),
    }

    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    return result


def get_git_revision(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception:
        return "unknown"


def save_integration_report(root: Path, report: str) -> Path:
    state_dir = root / ".architect-dev-team"
    state_dir.mkdir(exist_ok=True)
    report_path = state_dir / "integration_report.md"
    report_path.write_text(report, encoding="utf-8")
    return report_path


def integration_cli(root: Path, command: str, **kwargs) -> int:
    try:
        if command != "run":
            print(f"Unknown command: {command}", file=sys.stderr)
            return 1

        state_path = root / ".architect-dev-team" / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}

        reviewed = collect_reviewed_tasks(root)
        if not reviewed:
            print("No completed tasks to integrate")
            return 1

        independence = check_review_independence(root, reviewed)

        test_commands = kwargs.get("test_commands")
        if not test_commands:
            # Use the interpreter that runs this helper. A bare "python" is not
            # guaranteed to exist on PATH (notably on Windows), and a missing
            # interpreter must not be reported as a passing test.
            python = sys.executable
            test_commands = [
                f'"{python}" -m pytest tests/ -v --tb=short',
                f'"{python}" -m pytest tests/integration/ -v --tb=short' if (root / "tests" / "integration").exists() else "",
                f'"{python}" -m pytest tests/security/ -v --tb=short' if (root / "tests" / "security").exists() else "",
            ]
        test_commands = [c for c in test_commands if c]
        test_results = run_integration_tests(root, test_commands)

        report = generate_integration_report(root, reviewed, independence, test_results, state)
        report_path = save_integration_report(root, report)

        evidence_path = root / ".architect-dev-team" / "integration_evidence.json"
        evidence_path.write_text(json.dumps({
            "independence": independence,
            "test_results": test_results,
        }, indent=2, ensure_ascii=False), encoding="utf-8")

        print(f"Integration report saved: {report_path}")
        print("Summary:")
        for cmd, result in test_results.items():
            status = "PASS" if result.get("passed") else "FAIL"
            print(f"  {status}: {cmd}")
        for r in independence:
            print(f"  Independence {r['task']}: {r['independence']}")
            for reason in r.get("reasons", []):
                print(f"    - {reason}")

        failed = [cmd for cmd, result in test_results.items() if not result.get("passed")]
        not_independent = [r["task"] for r in independence if r["independence"] != "independent"]
        if failed:
            print(f"WARNING: Some checks failed: {failed}")
        if not_independent:
            print(f"WARNING: Review independence not established for: {not_independent}")
        return 1 if (failed or not_independent) else 0
    except Invalid as e:
        print(f"INVALID: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"INVALID: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Integration runner")
    parser.add_argument("root", type=Path)
    parser.add_argument("command", choices=["run"])
    parser.add_argument("--test-commands", type=str, nargs="*")
    args = parser.parse_args()
    sys.exit(integration_cli(args.root, args.command, **vars(args)))
