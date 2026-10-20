"""
Automated project intake: discovery → gap analysis → structured questions → versioned brief.
Python 3.10+, stdlib only. Read-only; no execution, network, or state mutation.
"""
from __future__ import annotations
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .inventory import inventory
from .common import Invalid


@dataclass
class BriefSection:
    """A section of the project brief with evidence."""
    key: str
    label: str
    required: bool
    evidence: list[str] = field(default_factory=list)
    value: Optional[str] = None
    assumption: Optional[str] = None
    critical: bool = False


@dataclass
class Question:
    """A single intake question."""
    id: str
    section: str
    text: str
    context: str
    default: Optional[str] = None
    critical: bool = False


@dataclass
class ProjectBrief:
    """Complete project brief structure."""
    version: str
    project_id: str
    discovery_summary: dict[str, Any]
    goals: dict[str, str]
    scope_in: list[str]
    scope_out: list[str]
    platform: dict[str, Any]
    domain: dict[str, Any]
    design: dict[str, Any]
    constraints: dict[str, Any]
    assumptions: list[dict[str, Any]]
    risks: list[dict[str, Any]]
    open_decisions: list[str]
    next_action: str

    def to_markdown(self, template_path: Path) -> str:
        """Render brief using template."""
        template = template_path.read_text(encoding="utf-8")
        # Simple placeholder substitution
        replacements = {
            "<project_id>": self.project_id,
            "<version>": self.version,
            "<timestamp>": self.version.split("-")[0],
            "<key findings from inventory>": self._fmt_discovery("observations"),
            "<likely stack>": self._fmt_discovery("inferences"),
            "<inferred needs with evidence paths>": self._fmt_discovery("capability_needs"),
            "<explicit gaps>": self._fmt_discovery("unknowns"),
            "<who uses this>": self.goals.get("audience", ""),
            "<core problem statement>": self.goals.get("problem", ""),
            "<single most important measurable outcome>": self.goals.get("success", ""),
            "<function 1>": self._fmt_list(self.scope_in),
            "<excluded feature 1>": self._fmt_list(self.scope_out),
            "<web / mobile / desktop / CLI / library / service>": self.platform.get("target", ""),
            "<languages, frameworks, key deps from discovery>": self.platform.get("stack", ""),
            "<external APIs, services, databases>": self.platform.get("integrations", ""),
            "<models, storage, migration needs>": self.platform.get("data", ""),
            "<deployment, monitoring, scaling, compliance>": self.platform.get("operations", ""),
            "<finance / science / gaming / ML / etc. or \"none\">": self.domain.get("specialist", "none"),
            "<SI, domain-specific>": self.domain.get("units", ""),
            "<precision, error bounds>": self.domain.get("tolerances", ""),
            "<known good results, standards>": self.domain.get("reference_values", ""),
            "<named methods, citations>": self.domain.get("algorithms", ""),
            "<must-hold properties>": self.domain.get("invariants", ""),
            "<minimal / branded / playful / professional / etc.>": self.design.get("direction", ""),
            "<URLs, screenshots, design systems>": self.design.get("references", ""),
            "<WCAG level, specific requirements>": self.design.get("accessibility", ""),
            "<critical user flows>": self.design.get("interactions", ""),
            "<cost ceiling, token limits, paid API policy>": self.constraints.get("budget", ""),
            "<data residency, PII handling, encryption>": self.constraints.get("privacy", ""),
            "<approved / forbidden model or service providers>": self.constraints.get("providers", ""),
            "<local-first / cloud-ok / hybrid>": self.constraints.get("autonomy", ""),
            "<default>": self._fmt_assumptions(),
            "<risk>": self._fmt_risks(),
            "<critical question 1>": self._fmt_open_decisions(),
        }
        result = template
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)
        return result

    def _fmt_discovery(self, key: str) -> str:
        items = self.discovery_summary.get(key, [])
        if not items:
            return "(none observed)"
        lines = []
        for item in items[:10]:
            if isinstance(item, dict):
                evidence = item.get('evidence', {})
                if isinstance(evidence, dict):
                    evidence_str = evidence.get('path', '')
                elif isinstance(evidence, list):
                    evidence_str = ", ".join(str(e) for e in evidence[:3])
                else:
                    evidence_str = str(evidence)
                lines.append(f"- {item.get('kind', '')}: {item.get('value', item.get('need', ''))} [{evidence_str}]")
            else:
                lines.append(f"- {item}")
        return "\n".join(lines)

    def _fmt_list(self, items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items) if items else "(none)"

    def _fmt_assumptions(self) -> str:
        if not self.assumptions:
            return "| (none) | | |\n| --- | --- | --- |"
        lines = []
        for a in self.assumptions:
            lines.append(f"| {a.get('assumption', '')} | {a.get('source', '')} | {'Yes' if a.get('reversible') else 'No'} |")
        return "\n".join(lines)

    def _fmt_risks(self) -> str:
        if not self.risks:
            return "| (none) | | | |\n| --- | --- | --- | --- |"
        lines = []
        for r in self.risks:
            lines.append(f"| {r.get('risk', '')} | {r.get('likelihood', '')} | {r.get('impact', '')} | {r.get('mitigation', '')} |")
        return "\n".join(lines)

    def _fmt_open_decisions(self) -> str:
        return "\n".join(f"- {d}" for d in self.open_decisions) if self.open_decisions else "(none)"


def discover_project(root: Path) -> dict[str, Any]:
    """Run inventory and gather repository context."""
    inv = inventory(root)
    # Read key repository files
    context = {}
    for name in ("AGENTS.md", "CLAUDE.md", "README.md", "README"):
        path = root / name
        if path.exists():
            try:
                context[name] = path.read_text(encoding="utf-8")[:5000]
            except Exception:
                pass
    return {
        "inventory": inv,
        "repo_context": context,
    }


def analyze_gaps(discovery: dict[str, Any]) -> list[BriefSection]:
    """Identify missing brief sections based on discovery."""
    inv = discovery["inventory"]
    sections = [
        BriefSection("goals.audience", "Target audience", True, critical=True),
        BriefSection("goals.problem", "Core problem", True, critical=True),
        BriefSection("goals.success", "Primary success metric", True, critical=True),
        BriefSection("scope_in", "Must-have features / MVP", True, critical=True),
        BriefSection("scope_out", "Explicit non-goals", True),
        BriefSection("platform.target", "Target platform", True,
                     evidence=[p["evidence"]["path"] for p in inv.get("inferences", []) if "platform" in p.get("value", "").lower()]),
        BriefSection("platform.stack", "Existing stack", False,
                     evidence=[p["evidence"]["path"] for p in inv.get("observations", []) if p.get("kind") == "manifest"]),
        BriefSection("platform.integrations", "Integrations", False),
        BriefSection("platform.data", "Data models & storage", False),
        BriefSection("platform.operations", "Operations & deployment", False),
        BriefSection("domain.specialist", "Specialist domain", False),
        BriefSection("domain.units", "Units & measurements", False),
        BriefSection("domain.tolerances", "Tolerances & precision", False),
        BriefSection("domain.reference_values", "Reference values", False),
        BriefSection("domain.algorithms", "Algorithms & formulas", False),
        BriefSection("domain.invariants", "Invariants", False),
        BriefSection("design.direction", "Design direction", False),
        BriefSection("design.references", "Design references", False),
        BriefSection("design.accessibility", "Accessibility requirements", False),
        BriefSection("design.interactions", "Key interactions", False),
        BriefSection("constraints.budget", "Budget & cost limits", False),
        BriefSection("constraints.privacy", "Privacy & data residency", False),
        BriefSection("constraints.providers", "Approved/forbidden providers", False),
        BriefSection("constraints.autonomy", "Autonomy preference", False),
    ]
    # Mark sections with evidence as having reversible defaults
    for s in sections:
        if s.evidence:
            s.assumption = f"Inferred from {', '.join(s.evidence[:3])}"
    return sections


def generate_questions(sections: list[BriefSection], max_per_block: int = 5) -> list[list[Question]]:
    """Group missing critical/important sections into question blocks."""
    missing = [s for s in sections if s.value is None and (s.required or s.critical)]
    # Sort: critical first, then required, then by evidence availability
    missing.sort(key=lambda s: (not s.critical, not s.required, len(s.evidence) == 0))

    blocks = []
    current_block = []
    for s in missing:
        q = Question(
            id=s.key.replace(".", "_"),
            section=s.key,
            text=_question_text(s.key),
            context=s.assumption or "No inference available.",
            default=_default_for(s.key),
            critical=s.critical,
        )
        current_block.append(q)
        if len(current_block) >= max_per_block:
            blocks.append(current_block)
            current_block = []
    if current_block:
        blocks.append(current_block)
    return blocks


def _question_text(key: str) -> str:
    texts = {
        "goals.audience": "Who are the primary users or consumers of this project?",
        "goals.problem": "What core problem does this project solve?",
        "goals.success": "What single outcome would make this project a clear success?",
        "scope_in": "What are the must-have features for the MVP?",
        "scope_out": "What features are explicitly excluded (non-goals)?",
        "platform.target": "What is the target platform (web, mobile, desktop, CLI, library, service)?",
        "platform.stack": "What is the existing tech stack? (inferred from repo)",
        "platform.integrations": "Which external APIs, services, or databases must integrate?",
        "platform.data": "What are the key data models and storage requirements?",
        "platform.operations": "What are the deployment, monitoring, and scaling requirements?",
        "domain.specialist": "Does this require specialist domain knowledge (finance, science, gaming, ML, etc.)?",
        "domain.units": "What units of measurement are used?",
        "domain.tolerances": "What precision, error bounds, or tolerances apply?",
        "domain.reference_values": "Are there known reference values or standards to validate against?",
        "domain.algorithms": "Are there specific algorithms, formulas, or methods required?",
        "domain.invariants": "What properties must always hold (invariants)?",
        "design.direction": "What is the visual/design direction?",
        "design.references": "Any design references, screenshots, or design systems?",
        "design.accessibility": "What accessibility level is required (WCAG AA, AAA, etc.)?",
        "design.interactions": "What are the critical user interactions or flows?",
        "constraints.budget": "What is the cost ceiling or token budget?",
        "constraints.privacy": "Any data residency, PII, or encryption requirements?",
        "constraints.providers": "Any approved or forbidden model/service providers?",
        "constraints.autonomy": "Preference: local-first, cloud-ok, or hybrid?",
    }
    return texts.get(key, f"Please provide: {key}")


def _default_for(key: str) -> Optional[str]:
    defaults = {
        "platform.target": "web",
        "platform.stack": "(inferred from repository)",
        "design.direction": "clean, accessible, system-default",
        "design.accessibility": "WCAG 2.1 AA",
        "constraints.autonomy": "local-first preferred",
    }
    return defaults.get(key)


def compile_brief(
    discovery: dict[str, Any],
    answers: dict[str, str],
    sections: list[BriefSection],
    project_id: str,
) -> ProjectBrief:
    """Build ProjectBrief from discovery and user answers."""
    # Apply answers to sections
    for s in sections:
        if s.key in answers:
            s.value = answers[s.key]

    # Generate version hash from inputs
    version_input = json.dumps({
        "discovery": discovery["inventory"],
        "answers": answers,
    }, sort_keys=True).encode()
    version_hash = hashlib.sha256(version_input).hexdigest()[:12]
    from datetime import datetime
    version = f"{datetime.now().isoformat(timespec='seconds')}-{version_hash}"

    # Build structured brief
    brief = ProjectBrief(
        version=version,
        project_id=project_id,
        discovery_summary={
            "observations": discovery["inventory"].get("observations", []),
            "inferences": discovery["inventory"].get("inferences", []),
            "capability_needs": discovery["inventory"].get("capability_needs", []),
            "unknowns": discovery["inventory"].get("unknowns", []),
        },
        goals={
            "audience": _get(sections, "goals.audience") or "",
            "problem": _get(sections, "goals.problem") or "",
            "success": _get(sections, "goals.success") or "",
        },
        scope_in=_get_list(sections, "scope_in"),
        scope_out=_get_list(sections, "scope_out"),
        platform={
            "target": _get(sections, "platform.target") or "",
            "stack": _get(sections, "platform.stack") or "",
            "integrations": _get(sections, "platform.integrations") or "",
            "data": _get(sections, "platform.data") or "",
            "operations": _get(sections, "platform.operations") or "",
        },
        domain={
            "specialist": _get(sections, "domain.specialist") or "none",
            "units": _get(sections, "domain.units") or "",
            "tolerances": _get(sections, "domain.tolerances") or "",
            "reference_values": _get(sections, "domain.reference_values") or "",
            "algorithms": _get(sections, "domain.algorithms") or "",
            "invariants": _get(sections, "domain.invariants") or "",
        },
        design={
            "direction": _get(sections, "design.direction") or "",
            "references": _get(sections, "design.references") or "",
            "accessibility": _get(sections, "design.accessibility") or "",
            "interactions": _get(sections, "design.interactions") or "",
        },
        constraints={
            "budget": _get(sections, "constraints.budget") or "",
            "privacy": _get(sections, "constraints.privacy") or "",
            "providers": _get(sections, "constraints.providers") or "",
            "autonomy": _get(sections, "constraints.autonomy") or "",
        },
        assumptions=[
            {"assumption": s.assumption or "", "source": "discovery" if s.evidence else "user", "reversible": bool(s.assumption)}
            for s in sections if s.assumption
        ],
        risks=[],  # Populated later by architecture team
        open_decisions=[
            s.key for s in sections if s.value is None and s.critical
        ],
        next_action="architecture" if any(s.value is None and s.critical for s in sections) else "lean_delivery",
    )
    return brief


def _get(sections: list[BriefSection], key: str) -> Optional[str]:
    for s in sections:
        if s.key == key:
            return s.value
    return None


def _get_list(sections: list[BriefSection], key: str) -> list[str]:
    val = _get(sections, key)
    if not val:
        return []
    # Split by lines, commas, or semicolons
    items = re.split(r"[\n,;]+", val)
    return [item.strip() for item in items if item.strip()]


def run_intake(root: Path, project_id: Optional[str] = None, non_interactive: bool = False) -> ProjectBrief:
    """Main intake workflow. In non-interactive mode, uses defaults for non-critical gaps."""
    if not root.exists() or not root.is_dir():
        raise Invalid(f"Project root not found: {root}")

    discovery = discover_project(root)
    sections = analyze_gaps(discovery)

    if non_interactive:
        # Fill non-critical with defaults, leave critical as None
        for s in sections:
            if s.value is None and not s.critical:
                s.value = _default_for(s.key) or "(tbd)"
    else:
        # Interactive mode would prompt user here
        # For now, simulate with defaults for demo
        for s in sections:
            if s.value is None:
                s.value = _default_for(s.key) or "(tbd)"

    if not project_id:
        project_id = root.name.lower().replace(" ", "-")

    brief = compile_brief(discovery, {}, sections, project_id)
    return brief


def save_brief(brief: ProjectBrief, root: Path) -> Path:
    """Save brief to .architect-dev-team/brief.md"""
    state_dir = root / ".architect-dev-team"
    state_dir.mkdir(exist_ok=True)
    brief_path = state_dir / "brief.md"
    template_path = Path(__file__).parent.parent.parent / "assets" / "brief.template.md"
    markdown = brief.to_markdown(template_path)
    brief_path.write_text(markdown, encoding="utf-8")
    return brief_path


# CLI entry point for validate.py
def intake_cli(root: Path, project_id: Optional[str] = None) -> int:
    """CLI wrapper for validate.py intake command."""
    try:
        brief = run_intake(root, project_id, non_interactive=True)
        brief_path = save_brief(brief, root)
        print(f"Brief saved to: {brief_path}")
        print(f"Project: {brief.project_id}")
        print(f"Version: {brief.version}")
        print(f"Next action: {brief.next_action}")
        if brief.open_decisions:
            print("Open decisions:")
            for d in brief.open_decisions:
                print(f"  - {d}")
        return 0
    except Invalid as e:
        print(f"INVALID: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"INVALID: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Project intake")
    parser.add_argument("root", type=Path)
    parser.add_argument("--project-id", type=str)
    args = parser.parse_args()
    sys.exit(intake_cli(args.root, args.project_id))