# Proposed V2 organizational requirements

Status: **future planning only**. Recorded from the user's M1b-completion/M1c
authorization request, Parts C/D. These additions do not amend any approved
proposal, schema, approval binding or M1c implementation scope. They describe
desired behavior, not shipped features. Implementation needs a later architecture
review and separate milestone authorization.

## Adaptive organization

Use direct work for trivial tasks. For substantial work, activate only leads and
specialists whose contribution justifies their context and coordination cost.
Do not instantiate departments to imitate an organization.

| Layer | Accountability |
| --- | --- |
| Master Lead / Engineering Director | Objectives, approved architecture, priorities, milestones, department selection, dependencies, integration, approval enforcement, cost and context efficiency. Give outcome-oriented assignments without micromanaging specialists. |
| Department Leads / Workstream Coordinators | Critically validate assignments, resolve or escalate missing details, map dependencies/interfaces, decompose bounded tasks, assign ownership, define acceptance/verification, select minimal specialists, review/reject incomplete work and return an integrated result. |
| Specialists | Deliver one bounded task with explicit inputs, ownership, acceptance and handoff. Do not expand scope or recursively spawn agents. |

Possible departments: Product/UX; Visual Design/Design Systems; Domain
Intelligence/Research; Architecture/Engineering; Integration/Platform; QA;
Security/Reliability; Content/Technical Writing. Roles are optional responsibilities,
not a standing roster. Specialists can include product/UX/visual/motion design,
science/mathematics, frontend/backend/integration engineering, testing, security,
accessibility and technical writing.

Proposed task flow:

```text
User → Master Lead → Department Lead → Specialists → Department Review
     → Cross-Department Integration → Independent QA → Master Lead → Human Approval
```

Every assignment needs a compact contract: objective, architecture revision,
boundaries, inputs/dependencies, output, acceptance, verification, owner, handoff
format and escalation conditions. Leads request extra specialists; the Master
Lead authorizes allocation. Department acceptance is accountable technical review,
not message forwarding. Consequential work needs a distinct independent reviewer;
specialists and leads cannot certify their own outputs as independent acceptance.
Human architecture/completion gates remain separate from all agent verdicts.

## Content and technical writing

Preferred future upstream: [Softaworks Agent Toolkit](https://github.com/softaworks/agent-toolkit).
Primary candidate: `skills/writing-clearly-and-concisely/SKILL.md`.
Candidate identity/path are user-provided research leads, **not verified metadata**.
No registry entry, download, installation, activation or execution is introduced
by this document. License, actual path, compatibility and immutable revision
must be verified before any trust promotion; installation and use consent remain
distinct. Do not download or execute the toolkit wholesale.

A proposed Content & Technical Writing Lead coordinates substantial prose:
website/product/marketing copy, technical documentation, READMEs, guides, PRs,
release notes, interface text, reports and explanations. Establish audience,
goal, tone/language/structure; obtain verified domain facts; outline; delegate
drafting; apply `writing-clearly-and-concisely`; optionally use `humanizer`;
use `crafting-effective-readmes` for README work; then review accuracy, clarity,
terminology and consistency before returning content to its owning team.

Required writing discipline does not permit silent installation. If the external
skill is unavailable or unsafe, disclose that it was not executed, request separate
installation approval when relevant, and use native accuracy/clarity checks in the
meantime. M1c uses native prose checks; it does not implement this routing system.

## Visual design

Propose a dedicated Visual Design Lead for substantial website/UI work. Its
responsibilities include creative direction, identity, typography, color,
composition, interaction, responsive behavior, motion, accessibility and visual
consistency. For substantial websites, propose two or three distinct approaches
before selection, covering concept, audience, references/rationale, typography,
palette, components, interaction, accessibility and implementation implications.
Record the actual human choice. No website implementation is authorized here.

User-provided research candidates, all unverified and unapproved for installation:

- [Taste Skill](https://github.com/Leonxlnx/taste-skill)
- [Impeccable](https://github.com/pbakaus/impeccable)
- [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
- [Anthropic skills](https://github.com/anthropics/skills), including Frontend Design
- [Vercel agent skills](https://github.com/vercel-labs/agent-skills), including Web Design Guidelines
- [Softaworks toolkit](https://github.com/softaworks/agent-toolkit), including Design System Starter
- [Official OpenAI skills](https://github.com/openai/skills), including Figma capabilities

Choose complementary responsibilities: creative direction, design-system
consistency, accessibility/review and browser verification. Do not activate
overlapping generators indiscriminately. Discovery, selection, trust review,
installation and execution are separate decisions. Existing M1b candidate records
retain their original classifications; this list adds no registry records.

## Future review deliverables

At a later gate propose bounded milestones for lead decomposition, structured
handoffs, department acceptance, cross-department integration, writing routing,
creative design orchestration and context/cost efficiency. Define resource limits,
file ownership, escalation, recovery and independent acceptance with native-tool
fallbacks. Use compact context instead of full conversation copies. Measure actual
delegation overhead, context cost, review effectiveness and integration quality
when runtime evidence permits; do not invent cost savings or model capabilities.
