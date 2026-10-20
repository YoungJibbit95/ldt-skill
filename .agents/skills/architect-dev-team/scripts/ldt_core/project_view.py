"""
Project View Generator: Creates readable Markdown+Mermaid overview from state, architecture, brief, tasks.
Python 3.10+, stdlib only.
"""
from __future__ import annotations
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .common import Invalid


def load_state(root: Path) -> dict[str, Any]:
    state_path = root / ".architect-dev-team" / "state.json"
    if not state_path.exists():
        # Return minimal default state for project-view generation
        return {
            "schema_version": 2,
            "phase": "INTAKE",
            "approval_stage": None,
            "profile": "balanced",
            "architecture": None,
            "milestone": {},
            "approvals": [],
            "checks": [],
            "review": None,
            "completed": [],
            "open_issues": [],
            "constraints": [],
            "next_action": "Inspect the relevant project and clarify acceptance criteria.",
            "brief": None,
            "research_results": [],
            "task_contracts": [],
            "project_view": None,
            "pair_results": [],
            "lead_session": None,
            "arch_lead_session": None,
            "effort": {"tokens": 0, "time_seconds": 0, "agents": 0, "repair_rounds": 0}
        }
    return json.loads(state_path.read_text(encoding="utf-8"))


def load_architecture(root: Path) -> str:
    arch_path = root / ".architect-dev-team" / "architecture.md"
    if not arch_path.exists():
        raise Invalid("Architecture not found")
    return arch_path.read_text(encoding="utf-8")


def load_brief(root: Path) -> Optional[str]:
    brief_path = root / ".architect-dev-team" / "brief.md"
    if brief_path.exists():
        return brief_path.read_text(encoding="utf-8")
    return None


def load_tasks(root: Path) -> list[dict[str, Any]]:
    tasks_dir = root / ".architect-dev-team" / "tasks"
    if not tasks_dir.exists():
        return []
    tasks = []
    for json_path in tasks_dir.glob("*.json"):
        try:
            tasks.append(json.loads(json_path.read_text(encoding="utf-8")))
        except Exception:
            pass
    return tasks


def load_research(root: Path) -> list[dict[str, Any]]:
    research_dir = root / ".architect-dev-team" / "research"
    if not research_dir.exists():
        return []
    research = []
    for json_path in research_dir.glob("*.json"):
        try:
            research.append(json.loads(json_path.read_text(encoding="utf-8")))
        except Exception:
            pass
    return research


def parse_architecture_sections(arch_content: str) -> dict[str, str]:
    """Extract sections from architecture.md"""
    sections = {}
    current_section = None
    current_content = []
    for line in arch_content.split("\n"):
        if line.startswith("## "):
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = line[3:].strip()
            current_content = []
        else:
            current_content.append(line)
    if current_section:
        sections[current_section] = "\n".join(current_content).strip()
    return sections


def parse_mermaid_from_architecture(arch_content: str) -> Optional[str]:
    """Extract mermaid diagram from architecture if present."""
    in_mermaid = False
    mermaid_lines = []
    for line in arch_content.split("\n"):
        if line.strip().startswith("```mermaid"):
            in_mermaid = True
            continue
        elif in_mermaid and line.strip().startswith("```"):
            in_mermaid = False
            break
        elif in_mermaid:
            mermaid_lines.append(line)
    return "\n".join(mermaid_lines) if mermaid_lines else None


def generate_text_diagram(arch_sections: dict[str, str]) -> str:
    """Generate text alternative from architecture sections."""
    design = arch_sections.get("Design", "")
    if not design:
        return "No design section in architecture."
    # Simple extraction of component references
    lines = []
    for line in design.split("\n"):
        line = line.strip()
        if line.startswith("-") or line.startswith("*"):
            lines.append(line)
        elif "component" in line.lower() or "service" in line.lower() or "boundary" in line.lower():
            lines.append(f"- {line}")
    return "\n".join(lines) if lines else "Architecture describes components and data flows; see Mermaid diagram."


def build_project_view(root: Path, status: str = "Entwurf") -> str:
    """Generate complete project view markdown."""
    state = load_state(root)
    architecture = load_architecture(root)
    brief = load_brief(root)
    tasks = load_tasks(root)
    research = load_research(root)

    arch_sections = parse_architecture_sections(architecture)
    mermaid = parse_mermaid_from_architecture(architecture)
    text_diagram = generate_text_diagram(arch_sections)

    # Extract key info
    project_id = root.name.lower().replace(" ", "-")
    arch_version = state.get("architecture", {}).get("sha256", "unknown")[:12] if state.get("architecture") else "unknown"
    brief_version = "unknown"
    if brief:
        for line in brief.split("\n"):
            if line.startswith("**Version**"):
                brief_version = line.split("**")[2].strip()
                break

    # Milestones from state
    milestone = state.get("milestone", {})
    milestones = []
    if milestone:
        milestones.append({
            "id": milestone.get("id", "M1"),
            "deliverable": milestone.get("summary", ""),
            "acceptance": ", ".join(milestone.get("acceptance", [])),
            "checks": ", ".join(milestone.get("required_checks", [])),
            "dependencies": "",
            "status": "planned"
        })

    # Tasks table
    task_rows = []
    for t in tasks:
        task_rows.append({
            "task_id": t.get("task_id", ""),
            "role": t.get("role", ""),
            "goal": t.get("goal", ""),
            "review_by": t.get("review_assignment", ""),
            "status": t.get("status", "created"),
            "agent": t.get("agent"),
            "model": t.get("model"),
            "session_id": t.get("session_id"),
            "execution_mode": t.get("execution_mode"),
        })

    # Skills from state/registry
    skill_rows = []
    # Would load from registry; placeholder
    skill_rows.append({
        "skill": "(from registry)",
        "version": "<rev>",
        "install_status": "pending",
        "consent": "pending",
        "used_by": ""
    })

    # Model profiles
    profile = state.get("profile", "balanced")
    profile_note = {
        "lean": "Lean: one slice, short design, self review labelled as such",
        "balanced": "Balanced: delegated work with one independent review",
        "rigorous": "Rigorous: separated design, implementation and test work",
    }.get(profile, profile)
    research_rows = []
    for item in research:
        if not isinstance(item, dict):
            continue
        research_rows.append(
            f"| {item.get('task_id', '—')} | {item.get('role', '—')} | "
            f"{item.get('status', '—')} | {item.get('agent', '—')} | "
            f"{item.get('model', '—')} | {item.get('confidence', '—')} |")
    runtime_rows = []
    for t in task_rows:
        runtime_rows.append(
            f"| {t['task_id']} | {t.get('agent') or '—'} | {t.get('model') or '—'} | "
            f"{t.get('session_id') or '—'} | {t.get('execution_mode') or '—'} |")

    # Risks from architecture
    risks = []
    risks_section = arch_sections.get("Risks and recovery", "")
    for line in risks_section.split("\n"):
        if line.strip().startswith("-"):
            risks.append(line.strip()[1:].strip())

    # Research results contribute their own risks and decisions.
    for item in research:
        if isinstance(item, dict) and item.get("role"):
            risks.append(f"[{item.get('task_id', 'research')}] "
                         f"{item.get('recommendation') or item.get('role')}")

    # Open decisions from brief
    open_decisions = []
    if brief:
        for line in brief.split("\n"):
            if "Open Decisions" in line or "open_decisions" in line.lower():
                # Parse following lines
                pass

    # Mandatory checks
    mandatory_checks = milestone.get("required_checks", []) if milestone else []

    # Render template
    template_path = Path(__file__).parent.parent.parent / "assets" / "project-view.template.md"
    template = template_path.read_text(encoding="utf-8")

    replacements = {
        "<project_id>": project_id,
        "<status>": status,
        "<arch_version>": arch_version,
        "<brief_version>": brief_version,
        "<timestamp>": datetime.now().isoformat(timespec="seconds"),
        "<goal>": milestone.get("summary", "TBD"),
        "<function 1>": "\n".join(f"- {a}" for a in milestone.get("acceptance", [])),
        "<Component A>": "Component A",
        "<Component B>": "Component B",
        "<Component C>": "Component C",
        "<Data Store>": "Data Store",
        "<Component A> calls <Component B> which calls <Component C> which reads/writes <Data Store>.": text_diagram,
        "<deliverable>": milestone.get("summary", ""),
        "<criteria>": ", ".join(milestone.get("acceptance", [])),
        "<checks>": ", ".join(milestone.get("required_checks", [])),
        "<deps>": "",
        "<status>": "planned",
        "<task-id>": "\n".join(f"| {t['task_id']} | {t['role']} | {t['goal'][:40]}... | {t['review_by'] or '—'} | {t['status']} |" for t in task_rows) if task_rows else "| (no tasks) | | | | |",
        "<runtime-row>": "\n".join(runtime_rows) if runtime_rows else "| (no tasks) | — | — | — | — |",
        "<profile-note>": profile_note,
        "<research-row>": "\n".join(research_rows) if research_rows else "| (no research) | — | — | — | — | — |",
        "<skill-id>": "\n".join(f"| {s['skill']} | {s['version']} | {s['install_status']} | {s['consent']} | {s['used_by']} |" for s in skill_rows),
        "<risk 1>": "\n".join(f"- {r}" for r in risks) if risks else "- (see architecture)",
        "<decision 1>": "\n".join(f"- {d}" for d in open_decisions) if open_decisions else "- (see brief)",
        "<check 1>": "\n".join(f"- {c}" for c in mandatory_checks),
    }

    # Handle mermaid diagram
    if mermaid:
        replacements["```mermaid\n    graph TD\n        A[Component A] --> B[Component B]\n        B --> C[Component C]\n        C --> D[Data Store]\n```"] = f"```mermaid\n{mermaid}\n```"

    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)

    return result


def save_project_view(root: Path, view: str, status: str = "Entwurf") -> Path:
    """Save project view to .architect-dev-team/project_view.md"""
    state_dir = root / ".architect-dev-team"
    state_dir.mkdir(exist_ok=True)
    view_path = state_dir / "project_view.md"
    view_path.write_text(view, encoding="utf-8")
    # Also save status marker
    (state_dir / "project_view_status.txt").write_text(status, encoding="utf-8")
    return view_path


def project_view_cli(root: Path, command: str, **kwargs) -> int:
    try:
        if command == "generate":
            status = kwargs.get("status", "Entwurf")
            view = build_project_view(root, status)
            path = save_project_view(root, view, status)
            print(f"Project view saved: {path}")
            print(view[:2000])
            return 0
        elif command == "status":
            status_path = root / ".architect-dev-team" / "project_view_status.txt"
            if status_path.exists():
                print(status_path.read_text(encoding="utf-8").strip())
            else:
                print("unknown")
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
    parser = argparse.ArgumentParser(description="Project view generator")
    parser.add_argument("root", type=Path)
    parser.add_argument("command", choices=["generate", "status"])
    parser.add_argument("--status", type=str, default="Entwurf")
    args = parser.parse_args()
    sys.exit(project_view_cli(args.root, args.command, **vars(args)))