"""
Research Specialist: Executes research tasks as a real native read-only agent.

Python 3.10+, stdlib only. The native `explore` agent is read-only, so a
research specialist cannot modify the project. When the runtime is unavailable
the module reports `unavailable` honestly and never fabricates findings.
"""
from __future__ import annotations
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .common import Invalid
from .runtime import dispatch, verify_session


@dataclass
class ResearchResult:
    task_id: str
    role: str
    question: str
    architecture_version: str
    date: str
    sources: list[dict[str, str]]
    findings: dict[str, Any]
    assumptions: list[dict[str, Any]]
    conflicts: list[dict[str, str]]
    applicability_limits: list[str]
    recommendation: str
    confidence: str  # High, Medium, Low
    blocking_decisions: list[str]
    # Runtime evidence
    status: str = "completed"
    session_id: Optional[str] = None
    agent: Optional[str] = None
    model: Optional[str] = None
    session_verified: bool = False
    execution_mode: str = "native"

    def to_markdown(self, template_path: Path) -> str:
        template = template_path.read_text(encoding="utf-8")
        def safe(value: Any) -> str:
            return str(value) if value is not None else ""
        replacements = {
            "<task_id>": safe(self.task_id),
            "<role>": safe(self.role),
            "<precise question>": safe(self.question),
            "<arch version>": safe(self.architecture_version),
            "<ISO8601>": safe(self.date),
            "<name>": self._fmt_sources_table(),
            "<official doc / standard / paper / spec>": "",
            "<version>": "",
            "<URL>": "",
            "<high/medium/low>": "",
            "<Detailed technical specifications, mathematical formulas, algorithm descriptions, pseudocode>": self.findings.get("specifications", ""),
            "<name>": self._fmt_units_table(),
            "<SI/domain>": "",
            "<metric/imperial/custom>": "",
            "<conversion if needed>": "",
            "<parameter>": self._fmt_tolerances_table(),
            "<e.g., 1e-6>": "",
            "<min–max>": "",
            "<standard / empirical / derived>": "",
            "<test_case>": self._fmt_references_table(),
            "<input>": "",
            "<output>": "",
            "<reference>": "",
            "<property 1>": self._fmt_invariants(),
            "<assumption>": self._fmt_assumptions_table(),
            "<source>": "",
            "<description>": "",
            "<claim>": self._fmt_conflicts_table(),
            "<ref>": "",
            "<contrary claim>": "",
            "<lead decision or open>": "",
            "<constraint 1: e.g., \"Valid for temperatures 0–100°C only\">": self._fmt_limits(),
            "<Concrete recommendation for architecture: component design, interface contract, algorithm choice, validation approach>": safe(self.recommendation),
            "<any open decisions needing human input>": ", ".join(self.blocking_decisions) if self.blocking_decisions else "None",
        }
        result = template
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)
        return result

    def _fmt_sources_table(self) -> str:
        if not self.sources:
            return "| (none) | | | | |\n| --- | --- | --- | --- | --- |"
        lines = []
        for s in self.sources:
            lines.append(f"| {s.get('name', '')} | {s.get('type', '')} | {s.get('version', '')} | {s.get('url', '')} | {s.get('credibility', '')} |")
        return "\n".join(lines)

    def _fmt_units_table(self) -> str:
        units = self.findings.get("units", [])
        if not units:
            return "| (none) | | | |\n| --- | --- | --- | --- |"
        lines = []
        for u in units:
            lines.append(f"| {u.get('quantity', '')} | {u.get('unit', '')} | {u.get('system', '')} | {u.get('notes', '')} |")
        return "\n".join(lines)

    def _fmt_tolerances_table(self) -> str:
        tols = self.findings.get("tolerances", [])
        if not tols:
            return "| (none) | | | |\n| --- | --- | --- | --- |"
        lines = []
        for t in tols:
            lines.append(f"| {t.get('parameter', '')} | {t.get('precision', '')} | {t.get('range', '')} | {t.get('basis', '')} |")
        return "\n".join(lines)

    def _fmt_references_table(self) -> str:
        refs = self.findings.get("reference_values", [])
        if not refs:
            return "| (none) | | |\n| --- | --- | --- |"
        lines = []
        for r in refs:
            lines.append(f"| {r.get('test_case', '')} | {r.get('expected', '')} | {r.get('source', '')} |")
        return "\n".join(lines)

    def _fmt_invariants(self) -> str:
        invs = self.findings.get("invariants", [])
        if not invs:
            return "(none)"
        return "\n".join(f"- {inv}" for inv in invs)

    def _fmt_assumptions_table(self) -> str:
        if not self.assumptions:
            return "| (none) | | | |\n| --- | --- | --- | --- |"
        lines = []
        for a in self.assumptions:
            lines.append(f"| {a.get('assumption', '')} | {a.get('source', '')} | {'Yes' if a.get('reversible') else 'No'} | {a.get('impact', '')} |")
        return "\n".join(lines)

    def _fmt_conflicts_table(self) -> str:
        if not self.conflicts:
            return "| (none) | | | | |\n| --- | --- | --- | --- | --- |"
        lines = []
        for c in self.conflicts:
            lines.append(f"| {c.get('finding_a', '')} | {c.get('source_a', '')} | {c.get('finding_b', '')} | {c.get('source_b', '')} | {c.get('resolution', '')} |")
        return "\n".join(lines)

    def _fmt_limits(self) -> str:
        if not self.applicability_limits:
            return "(none)"
        return "\n".join(f"- {limit}" for limit in self.applicability_limits)


RESEARCH_PROMPT = """You are the {role} research specialist answering one precise question for an
architecture team. You have read-only access to the project and may browse the web.

## Question
{question}

## Context
{context}

## Required outputs
{outputs}

## Rules
- Prefer official documentation, standards and original works.
- For every source record: name, type, version or date, URL, credibility.
- If sources disagree, record both and state the unresolved conflict.
- State applicability limits and uncertainty explicitly.
- Do NOT write or modify any project file. This is a specification task, not
  an implementation task.
- Do not claim verification you did not perform.
- Budget: at most 4 sources and at most 3 web lookups. Prefer the project's
  own files and the single most authoritative external source over breadth.
  An explicit, well-bounded answer beats an exhaustive one.

## Required output
Return ONLY a JSON object with these keys:
sources, findings, assumptions, conflicts, applicability_limits, recommendation,
confidence, blocking_decisions
- sources: list of {{name, type, version, url, credibility}}
- findings: object with keys specifications, units, tolerances, reference_values, invariants
  - units: list of {{quantity, unit, system, notes}}
  - tolerances: list of {{parameter, precision, range, basis}}
  - reference_values: list of {{test_case, expected, source}}
  - invariants: list of strings
- assumptions: list of {{assumption, source, reversible, impact}}
- conflicts: list of {{finding_a, source_a, finding_b, source_b, resolution}}
- applicability_limits: list of strings
- recommendation: string
- confidence: "High" | "Medium" | "Low"
- blocking_decisions: list of strings
"""


def execute_research(task: dict[str, Any], root: Path, template_path: Path) -> ResearchResult:
    """Execute a research task with a real native read-only agent."""
    question = str(task.get("question", ""))
    role = str(task.get("role", "Research"))
    context = str(task.get("context", ""))
    outputs = task.get("required_outputs") or []
    sources_hint = task.get("sources") or []

    prompt = RESEARCH_PROMPT.format(
        role=role,
        question=question,
        context=context,
        outputs="\n".join(f"- {o}" for o in outputs),
    )
    if sources_hint:
        prompt += "\n\n## Suggested starting points (verify each before citing)\n"
        prompt += "\n".join(f"- {s}" for s in sources_hint if isinstance(s, str))

    run = dispatch(prompt=prompt, role="research", cwd=root,
                   model_profile="medium", title=f"ldt research {task.get('task_id', '')}")

    if run.status == "unavailable":
        return ResearchResult(
            task_id=str(task.get("task_id", "research-001")),
            role=role, question=question,
            architecture_version=str(task.get("architecture_version", "")),
            date=datetime.now().isoformat(),
            sources=[], findings={}, assumptions=[], conflicts=[],
            applicability_limits=["Research could not run: OpenCode runtime unavailable."],
            recommendation="Research not performed. Runtime unavailable.",
            confidence="Low", blocking_decisions=["Research runtime unavailable"],
            status="unavailable", session_id=run.session_id,
            agent=run.agent, model=run.model, session_verified=False,
            execution_mode=run.evidence.get("execution_mode", "native"),
        )

    data = _parse(run.output)
    verified = False
    if run.session_id:
        verified = bool(verify_session(run.session_id, root).get("verified"))

    return ResearchResult(
        task_id=str(task.get("task_id", "research-001")),
        role=role, question=question,
        architecture_version=str(task.get("architecture_version", "")),
        date=datetime.now().isoformat(),
        sources=data.get("sources") or [],
        findings=data.get("findings") or {},
        assumptions=data.get("assumptions") or [],
        conflicts=data.get("conflicts") or [],
        applicability_limits=data.get("applicability_limits") or [],
        recommendation=str(data.get("recommendation") or ""),
        confidence=str(data.get("confidence") or "Low"),
        blocking_decisions=data.get("blocking_decisions") or [],
        status="completed" if run.status == "completed" else run.status,
        session_id=run.session_id, agent=run.agent, model=run.model,
        session_verified=verified,
        execution_mode=run.evidence.get("execution_mode", "native"),
    )


def _parse(text: str) -> dict[str, Any]:
    """Parse the agent's JSON output, tolerating fenced code blocks."""
    candidate = (text or "").strip()
    if not candidate:
        return {}
    if "```" in candidate:
        for part in candidate.split("```"):
            stripped = part.strip()
            if stripped.startswith("json"):
                stripped = stripped[4:]
            if stripped.startswith("{"):
                candidate = stripped
                break
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def save_result(result: ResearchResult, root: Path, template_path: Path) -> Path:
    """Save research result to .architect-dev-team/research/<task_id>.md"""
    research_dir = root / ".architect-dev-team" / "research"
    research_dir.mkdir(exist_ok=True)
    result_path = research_dir / f"{result.task_id}.md"
    result_path.write_text(result.to_markdown(template_path), encoding="utf-8")
    return result_path


def load_result(root: Path, task_id: str, template_path: Path) -> ResearchResult:
    result_path = root / ".architect-dev-team" / "research" / f"{task_id}.md"
    if not result_path.exists():
        raise Invalid(f"Research result not found: {result_path}")
    json_path = result_path.with_suffix(".json")
    if json_path.exists():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        return ResearchResult(**data)
    raise Invalid(f"Research result JSON not found: {json_path}")


def research_cli(root: Path, task_id: str, command: str) -> int:
    try:
        template_path = Path(__file__).parent.parent.parent / "assets" / "research.template.md"
        if command == "execute":
            plan_path = root / ".architect-dev-team" / "arch_team_plan.json"
            if not plan_path.exists():
                raise Invalid("Architecture team plan not found")
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            task = next((t for t in plan["research_tasks"] if t["task_id"] == task_id), None)
            if not task:
                raise Invalid(f"Task not found: {task_id}")
            task["architecture_version"] = plan["architecture_version"]
            result = execute_research(task, root, template_path)
            save_result(result, root, template_path)
            json_path = root / ".architect-dev-team" / "research" / f"{task_id}.json"
            json_path.write_text(json.dumps(asdict(result), indent=2, ensure_ascii=False), encoding="utf-8")
            for t in plan["research_tasks"]:
                if t["task_id"] == task_id:
                    t["status"] = result.status
                    t["result_path"] = f".architect-dev-team/research/{task_id}.md"
                    t["findings_summary"] = result.recommendation[:200] if result.recommendation else ""
                    break
            plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
            if result.status == "unavailable":
                print(f"UNAVAILABLE: research {task_id} could not run "
                      f"(OpenCode runtime unavailable). No findings were fabricated.")
                return 2
            print(f"Research result saved: {result.task_id} "
                  f"(agent={result.agent}, model={result.model}, "
                  f"session={result.session_id}, verified={result.session_verified})")
            return 0
        elif command == "status":
            plan_path = root / ".architect-dev-team" / "arch_team_plan.json"
            if not plan_path.exists():
                raise Invalid("Architecture team plan not found")
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            task = next((t for t in plan["research_tasks"] if t["task_id"] == task_id), None)
            if task:
                print(f"{task_id}: {task['status']}")
                return 0
            raise Invalid(f"Task not found: {task_id}")
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
    parser = argparse.ArgumentParser(description="Research specialist")
    parser.add_argument("root", type=Path)
    parser.add_argument("task_id", type=str)
    parser.add_argument("command", choices=["execute", "status"])
    args = parser.parse_args()
    sys.exit(research_cli(args.root, args.task_id, args.command))
