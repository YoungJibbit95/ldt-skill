# Architecture Team & Research Protocol

The Architecture Lead coordinates a small, task-specific research team.
No permanent roster — roles activated only when their contribution justifies cost.

## Roles

| Role | Responsibility | When Activated |
|------|----------------|----------------|
| **Architecture Lead** | Owns architecture document, integrates research, writes ADRs, defines milestones/checks | Always for non-Lean work |
| **System Architecture** | Boundaries, data flows, technology choices, tradeoffs, ADRs | Multi-component, integration-heavy |
| **Data / Interface** | Schemas, contracts, APIs, migration, compatibility, versioning | Changed interfaces, data models |
| **Domain Intelligence** | Specialist models, formulas, units, tolerances, reference values, invariants | Mathematical, scientific, financial, game mechanics |
| **Security / Trust** | Auth boundaries, secrets, permissions, supply chain, threat model | Auth changes, sensitive data, new dependencies |

## Research Task Contract

Each research assignment is a structured contract:

```json
{
  "task_id": "research-001",
  "role": "Domain Intelligence",
  "question": "Precise question to answer",
  "context": "Architecture version, milestone, related contracts",
  "required_outputs": [
    "Specifications / formulas / algorithms",
    "Units, tolerances, reference values",
    "Assumptions with sources",
    "Conflicting findings",
    "Applicability limits"
  ],
  "sources": [
    "Official documentation URLs",
    "Standards (RFC, ISO, IEEE)",
    "Original papers / authoritative sources"
  ],
  "deliverable": "research.template.md",
  "review_criteria": [
    "Source credibility & version",
    "Applicability to project constraints",
    "Uncertainty explicitly stated",
    "No production code — only specifications"
  ]
}
```

## Research Execution

1. Lead writes research contracts from brief + architecture gaps.
2. Each specialist runs independently (subagent or sequential pass).
3. Specialist returns: `research-<id>.md` with sources, versions, uncertainty.
4. Lead integrates into `architecture.md` — cites research by task_id.
5. Independent reviewer checks: follows consequential decisions, verifies sources.

## Research Output Template

See `assets/research.template.md`. Required sections:
- Question & context
- Sources (URL, version, date accessed)
- Findings (specifications, formulas, units, tolerances, reference values)
- Assumptions (reversible defaults marked)
- Conflicting evidence
- Applicability limits
- Recommendation for architecture

## Integration Rules

- Lead writes **single** architecture document; specialists contribute sections.
- No competing full architectures without explicit decision question.
- ADRs only for significant lasting decisions.
- Architecture contains only: components, data flows, contracts, security boundaries, tech decisions, ADRs, milestones, implementation packages.
- Independent reviewer validates consequential decisions **before** start gate.

## Escalation

- Unresolvable domain question → escalate to user with evidence.
- Conflicting sources → Lead documents tradeoff, requests human decision.
- Missing critical specification → blocks architecture approval.