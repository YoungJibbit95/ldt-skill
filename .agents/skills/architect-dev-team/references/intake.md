# Project Intake Protocol

Automated discovery and structured questioning for new or unclear projects.
Produces a versioned project brief that feeds architecture work.

## When intake runs

- New project or feature with missing goals, acceptance, key functions, data/security assumptions, platform decisions, or significant design constraints.
- Existing approved plan unchanged → skip intake.
- Small, well-described change → skip intake, proceed Lean.

## Discovery (read-only)

1. Run `inventory(root)` → observations, inferences, capability_needs, unknowns.
2. Read repository instructions (AGENTS.md, CLAUDE.md, README.md).
3. Inspect configs: package.json, pyproject.toml, Cargo.toml, go.mod, *.csproj, pom.xml, build.gradle.
4. Detect monorepo workspaces (apps/*, packages/*, services/*).
5. Record: languages, frameworks, platforms, test commands, deployment configs, installed skills (presence only).
6. Do not execute scripts, build tools, or network calls.

## Gap analysis

Compare discovery against required brief sections:

| Section | Required evidence | Reversible default |
|---------|-------------------|---------------------|
| Audience, problem, primary success | User statement | — |
| Must-have functions, MVP, explicit non-goals | User statement | — |
| Platform, stack, integrations, data, operations | Discovery + user | Current repo stack |
| Domain/scientific/math requirements | User statement | None |
| Design direction, references, accessibility, interactions | User statement | System defaults |
| Budget, privacy, allowed providers, desired autonomy | User statement | Local-only, no paid APIs |

Missing evidence → question. Sufficient evidence → mark as assumption with source.

## Question blocks (max 3–5 per block)

Present in small groups. Skip answered or reliably inferred.

1. **Goals & success**: Target users, core problem, single most important outcome.
2. **Scope**: Must-have features, MVP boundary, explicitly excluded features.
3. **Platform & data**: Target platform, existing stack/services, data models, operational constraints.
4. **Domain depth**: Mathematical, scientific, or specialist requirements; units, tolerances, reference values.
5. **Design & UX**: Visual direction, references, accessibility level, key interactions.
6. **Constraints**: Cost ceiling, data residency, approved/forbidden providers, autonomy preference.

Each question: context + reasoned default + criticality marker (critical/important/nice).

## Brief compilation

Template: `assets/brief.template.md` → output: `.architect-dev-team/brief.md`

Fields:
- `version`: ISO8601 timestamp + short hash of generating inputs
- `project_id`: slug from repository name or user input
- `discovery_summary`: key observations, inferences, unknowns
- `goals`: audience, problem, success metric
- `scope_in`: must-have functions, MVP
- `scope_out`: explicit non-goals
- `platform`: target, stack, integrations, data, operations
- `domain`: specialist requirements, units, tolerances, references
- `design`: direction, references, accessibility, interactions
- `constraints`: budget, privacy, providers, autonomy
- `assumptions`: reversible defaults with sources
- `risks`: identified technical, organizational, compliance risks
- `open_decisions`: critical unanswered questions blocking architecture
- `next_action`: "architecture" or "lean_delivery"

## Integration with validate.py

New read-only command:
```
python validate.py intake <project-root>
```
Outputs brief path and summary. Does not modify state.

## CLI usage (future)

`ldt intake` → same core, interactive question flow.