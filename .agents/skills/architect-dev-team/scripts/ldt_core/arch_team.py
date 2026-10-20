"""
Architecture Team: Lead decomposes brief into research tasks, integrates results.
Python 3.10+, stdlib only.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from .common import Invalid


@dataclass
class ResearchTask:
    task_id: str
    role: str
    question: str
    context: str
    required_outputs: list[str]
    sources: list[str]
    deliverable_template: str
    review_criteria: list[str]
    status: str = "pending"  # pending, in_progress, completed, blocked
    result_path: Optional[str] = None
    findings_summary: Optional[str] = None


@dataclass
class ArchitectureTeamPlan:
    architecture_version: str
    brief_version: str
    research_tasks: list[ResearchTask]
    lead_notes: str = ""
    independent_reviewer: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    @staticmethod
    def from_json(data: str) -> ArchitectureTeamPlan:
        d = json.loads(data)
        # Filter research task dicts to only known ResearchTask fields
        known_fields = {f.name for f in ResearchTask.__dataclass_fields__.values()}
        filtered_tasks = []
        for t in d["research_tasks"]:
            filtered = {k: v for k, v in t.items() if k in known_fields}
            filtered_tasks.append(ResearchTask(**filtered))
        d["research_tasks"] = filtered_tasks
        # Filter plan dict to known fields
        plan_known_fields = {f.name for f in ArchitectureTeamPlan.__dataclass_fields__.values()}
        filtered_plan = {k: v for k, v in d.items() if k in plan_known_fields}
        return ArchitectureTeamPlan(**filtered_plan)


def decompose_brief(brief_path: Path, architecture_template: Path) -> ArchitectureTeamPlan:
    """Analyze brief and architecture template → produce research task contracts."""
    brief_content = brief_path.read_text(encoding="utf-8")

    # Extract key gaps from brief (open_decisions, domain requirements, etc.)
    # This is a simplified heuristic; real implementation would parse the brief structure
    tasks = []
    task_counter = 0

    def add_task(role: str, question: str, context: str, sources: list[str]):
        nonlocal task_counter
        task_counter += 1
        tasks.append(ResearchTask(
            task_id=f"research-{task_counter:03d}",
            role=role,
            question=question,
            context=context,
            required_outputs=[
                "Specifications / formulas / algorithms",
                "Units, tolerances, reference values",
                "Assumptions with sources",
                "Conflicting findings",
                "Applicability limits",
            ],
            sources=sources,
            deliverable_template="research.template.md",
            review_criteria=[
                "Source credibility & version",
                "Applicability to project constraints",
                "Uncertainty explicitly stated",
                "No production code — only specifications",
            ],
        ))

    # Always need system architecture for non-trivial work
    add_task(
        "System Architecture",
        "What are the system boundaries, key components, data flows, and technology tradeoffs?",
        f"Brief: {brief_path.name}, Template: {architecture_template.name}",
        ["Project brief", "Existing architecture docs", "Technology documentation"],
    )

    # Check brief for domain requirements
    if "domain" in brief_content.lower() and ("specialist" in brief_content.lower() or "math" in brief_content.lower() or "scientific" in brief_content.lower()):
        add_task(
            "Domain Intelligence",
            "What are the precise mathematical models, formulas, units, tolerances, and reference values required?",
            f"Brief domain section: {brief_path.name}",
            ["Official standards (ISO, IEEE, RFC)", "Original research papers", "Authoritative domain references"],
        )

    # Check for security/auth requirements
    if any(kw in brief_content.lower() for kw in ["auth", "security", "secret", "permission", "privacy", "compliance"]):
        add_task(
            "Security / Trust",
            "What are the authentication boundaries, authorization model, secret management, and threat model?",
            f"Brief constraints & platform: {brief_path.name}",
            ["OWASP guidelines", "Platform security docs", "Compliance standards"],
        )

    # Check for data/interface requirements
    if any(kw in brief_content.lower() for kw in ["api", "schema", "contract", "migration", "integration", "data model"]):
        add_task(
            "Data / Interface",
            "What are the data schemas, API contracts, migration requirements, and compatibility constraints?",
            f"Brief platform & integrations: {brief_path.name}",
            ["OpenAPI/GraphQL specs", "Database docs", "Integration partner APIs"],
        )

    # Architecture version from brief hash
    arch_version = hashlib.sha256(brief_content.encode()).hexdigest()[:12]

    return ArchitectureTeamPlan(
        architecture_version=arch_version,
        brief_version=brief_path.stem,
        research_tasks=tasks,
        lead_notes=f"Decomposed from brief {brief_path.name} at {datetime.now().isoformat()}",
    )


def save_plan(plan: ArchitectureTeamPlan, root: Path) -> Path:
    """Save plan to .architect-dev-team/arch_team_plan.json"""
    state_dir = root / ".architect-dev-team"
    state_dir.mkdir(exist_ok=True)
    plan_path = state_dir / "arch_team_plan.json"
    plan_path.write_text(plan.to_json(), encoding="utf-8")
    return plan_path


def load_plan(root: Path) -> ArchitectureTeamPlan:
    plan_path = root / ".architect-dev-team" / "arch_team_plan.json"
    if not plan_path.exists():
        raise Invalid("Architecture team plan not found. Run decompose first.")
    return ArchitectureTeamPlan.from_json(plan_path.read_text(encoding="utf-8"))


def integrate_research(plan: ArchitectureTeamPlan, root: Path, architecture_template: Path) -> str:
    """Integrate completed research tasks into architecture.md"""
    template = architecture_template.read_text(encoding="utf-8")
    research_dir = root / ".architect-dev-team" / "research"
    research_dir.mkdir(exist_ok=True)

    # Collect research results. A fixture run is not research evidence: it is
    # marked as such and excluded from the architecture document.
    research_results = {}
    fixture_results = []
    for task in plan.research_tasks:
        if task.status == "completed" and task.result_path:
            result_path = root / task.result_path
            if not result_path.exists():
                continue
            json_path = result_path.with_suffix(".json")
            mode = "native"
            if json_path.exists():
                try:
                    recorded = json.loads(json_path.read_text(encoding="utf-8"))
                    mode = str(recorded.get("execution_mode", "native"))
                except (OSError, UnicodeError, json.JSONDecodeError):
                    mode = "unknown"
            if mode != "native":
                fixture_results.append(f"{task.task_id} ({mode})")
                continue
            research_results[task.task_id] = result_path.read_text(encoding="utf-8")
    if fixture_results:
        research_results["__excluded_fixture__"] = ", ".join(fixture_results)

    # Build architecture document
    sections = {
        "Outcome and scope": f"Derived from brief {plan.brief_version}. Research: {len(research_results)} tasks completed.",
        "Requirements and assumptions": _build_requirements_section(research_results),
        "Design": _build_design_section(research_results),
        "Risks and recovery": _build_risks_section(research_results),
        "Milestones": _build_milestones_section(research_results),
        "Approval requested": f"Architecture version {plan.architecture_version}. Research tasks: {', '.join(r for r in research_results)}.",
    }

    # Replace template sections
    result = template
    for key, content in sections.items():
        placeholder = f"## {key}"
        if placeholder in result:
            # Find section and replace content until next ## or end
            lines = result.split("\n")
            new_lines = []
            in_section = False
            for line in lines:
                if line.startswith(placeholder):
                    in_section = True
                    new_lines.append(line)
                    new_lines.append(content)
                    continue
                if in_section and line.startswith("## ") and line != placeholder:
                    in_section = False
                if not in_section or line == placeholder:
                    new_lines.append(line)
            result = "\n".join(new_lines)

    return result


def _build_requirements_section(research: dict[str, str]) -> str:
    lines = ["Functional and non-functional requirements from research:"]
    for task_id, content in research.items():
        lines.append(f"\n### {task_id}")
        # Extract key findings (simplified)
        for line in content.split("\n"):
            if any(kw in line.lower() for kw in ["specification", "formula", "unit", "tolerance", "reference", "invariant", "assumption"]):
                lines.append(f"- {line.strip()}")
    return "\n".join(lines)


def _build_design_section(research: dict[str, str]) -> str:
    lines = ["Architecture design informed by research:"]
    for task_id, content in research.items():
        lines.append(f"\n### {task_id} Contributions")
        for line in content.split("\n"):
            if any(kw in line.lower() for kw in ["recommendation", "component", "interface", "boundary", "technology", "tradeoff"]):
                lines.append(f"- {line.strip()}")
    return "\n".join(lines)


def _build_risks_section(research: dict[str, str]) -> str:
    lines = ["Risks identified from research:"]
    for task_id, content in research.items():
        for line in content.split("\n"):
            if any(kw in line.lower() for kw in ["risk", "conflict", "uncertain", "limit", "blocking"]):
                lines.append(f"- [{task_id}] {line.strip()}")
    return "\n".join(lines) if len(lines) > 1 else "No significant risks identified from research."


def _build_milestones_section(research: dict[str, str]) -> str:
    return """| ID | Deliverable | Acceptance | Required checks | Dependencies |
| --- | --- | --- | --- | --- |
| M1 | Core vertical slice | <observable behavior> | unit-tests, contract-tests, pair-review, integration-tests | Research complete |
| M2 | <next slice> | <observable behavior> | <checks> | M1 complete |"""


# CLI for validate.py
def arch_team_cli(root: Path, command: str, **kwargs) -> int:
    try:
        if command == "decompose":
            brief_path = root / ".architect-dev-team" / "brief.md"
            template_path = Path(__file__).parent.parent.parent / "assets" / "architecture.template.md"
            plan = decompose_brief(brief_path, template_path)
            save_plan(plan, root)
            print(f"Architecture team plan created with {len(plan.research_tasks)} research tasks")
            for t in plan.research_tasks:
                print(f"  {t.task_id}: {t.role} - {t.question[:60]}...")
            return 0
        elif command == "integrate":
            plan = load_plan(root)
            template_path = Path(__file__).parent.parent.parent / "assets" / "architecture.template.md"
            architecture = integrate_research(plan, root, template_path)
            arch_path = root / ".architect-dev-team" / "architecture.md"
            arch_path.write_text(architecture, encoding="utf-8")
            print(f"Architecture saved to: {arch_path}")
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
    import sys
    import argparse
    parser = argparse.ArgumentParser(description="Architecture team orchestration")
    parser.add_argument("root", type=Path)
    parser.add_argument("command", choices=["decompose", "integrate"])
    args = parser.parse_args()
    sys.exit(arch_team_cli(args.root, args.command))