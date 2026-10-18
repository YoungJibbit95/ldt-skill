# Little Dev Team V2 architecture proposal — revision 1

**Status: PROPOSED, NOT APPROVED OR IMPLEMENTED.** Date: 2026-10-18.
V1 hardening is implemented separately; V2 work stops at the approval gate.

## Scope and evidence boundary

Extend the existing `architect-dev-team`, retaining its native Codex entrypoint,
small milestones, human decisions, durable project memory, and optional external
skills. Add dynamic domain/product expertise, traceable integration, contextual
skill selection, and an optional `ldt` terminal interface in separately approved
increments. This is not a permanent agent roster or a background execution service.

The active hardening uses **state/snapshot schema 2** and **registry schema 1**.
The V2 product name is not either schema version. Rich project state will require
an explicit future schema revision; registry schema 2 below is proposed only.
No V2 role system, Skill Manager, CLI, new registry schema, SDK, or service exists.

Companion designs:

- [Skill ecosystem and inventory](v2-skill-ecosystem.md).
- [Optional CLI and verified runtime boundaries](v2-cli.md).
- [Security and approval threat model](v2-security.md).
- [A–D source inventory](research/skills-a-d.md), [E–I source inventory](research/skills-e-i.md),
  [runtime/library research](research/runtime-cli.md).

## Architecture and ownership

```text
Native Codex conversation                 Optional ldt CLI / plain text / JSON
         |                                           |
         +------ proposal, evidence, exact decision --+
                              |
                   Shared deterministic core
             state / scope / policy / snapshots / receipts
                  capability needs / registry queries
                              |
                Runtime adapter capability boundary
          manual session -> bounded exec -> optional app-server
                              |
          actual available agents, tools and approved local actions
```

The **Master Orchestrator** is the single coordination authority. It classifies
work, chooses effort, owns the architecture, sequences milestones, selects roles,
integrates findings, and asks for human decisions. Department leads propose work;
only the Master allocates additional agents. Every worker has explicit ownership,
output/evidence requirements, and stop conditions. No recursive delegation.

The shared core computes validity and action prerequisites, not human judgment.
It contains no model prompts, API credentials, UI, automatic network access, or
authority to approve itself. Runtime permissions and OS/CI controls remain separate.

The CLI renders decisions and forwards exact operator choices to that same core.
It must not implement an alternative approval or milestone state machine. Native
Codex use remains supported without installing the CLI or its terminal dependency.
Native explanations, approval questions, skill shortlists and result summaries
follow the user's language choice (initially English/German), with stable internal
IDs and digests independent of presentation language.

## Dynamic organization

Departments are routing categories. Use a parameterized role contract instead of
one file/process per job title. A person-sized task may need one agent with logical
role passes. Distinct agents are reserved for useful parallelism or independence.

| Domain | Responsibilities and possible specialties | Activation condition |
| --- | --- | --- |
| Leadership / architecture | Master, solution/architecture review, requirement decomposition, budgets and risk | Master always; architect/reviewer only for meaningful boundaries/tradeoffs |
| Product & Design | Product management, user research, UX architecture, art direction, visual/design systems, interaction/motion, accessibility, visual QA | User-facing behavior, visual requirements, or material usability risk |
| Domain Intelligence | Domain Intelligence Lead; mathematics, physics, numerical methods, geometry, data science, cryptography, industry/regulatory or creative expertise | Behavior depends on specialized assumptions, models, standards, or evidence |
| Engineering | Backend/frontend/database/native, integration, performance, refactoring, DevOps; Domain Integration Engineer | Approved code/interface/infrastructure scope |
| Quality & Assurance | Test, independent code/architecture/security/domain/integration/accessibility/performance/release reviewers | Risk and approved check policy; independence uses a distinct agent or human |
| Research / documentation | Authoritative-source research, external capability discovery, concise contracts/ADRs/handoffs/onboarding | Specific evidence or documentation gap; no redundant parallel document store |

The Domain Intelligence Lead is a responsibility the Master may perform directly.
It identifies subject areas, consequential questions, constraints and uncertainty;
recommends narrowly scoped experts; and checks handoffs. It does not independently
install tools, spawn agents, expand scope, or authorize engineering implementation.

## Allocation and task contract

Evaluate scope, domain sensitivity, irreversibility, interfaces, uncertainty, and
available capabilities before allocating work. Start Lean for tiny work, Balanced
by default, Rigorous for consequential domain/security/migration risk. Profiles
never weaken exact approval or mandatory policy.

1. Identify outcomes/affected contracts; reuse verified facts that remain current.
2. Choose the smallest useful expertise set and explain each role's contribution.
3. Use one worker for a sequential task; parallelize independent reads or disjoint
   writes only. Tests with shared fixtures also need ownership/isolation.
4. Preview substantial teams with roles, reasons, outputs, checkpoints and known
   cost signals. User may reduce/change the team. Don't invent currency/token costs.
5. Escalate reasoning or allocate a new specialist only for a concrete unresolved
   question. If budgets/tools aren't supported, bound tasks/output and report limits.

Task envelope (versioned independently of project state):

```text
task_id; objective; role + specialty; project/root/base revision;
approved scope + milestone; relevant domain/design contract IDs and hashes;
minimum source paths/facts; inputs; allowed tools/actions and file ownership;
constraints; expected outputs; acceptance; mandatory evidence/check IDs;
time/token limit if supported; escalation and cancellation conditions.
```

Result: task ID, observations/changes, affected paths/contracts, commands/outcomes,
evidence references, limitations/confidence, blockers, next action. No full chat or
raw-log dump. Workers cannot approve, install, post messages, publish, merge, deploy,
or act outside their task authority. A worker may request another expert, not spawn it.

## Domain workflow and engineering integration

For a significant domain-dependent feature:

`Question → Authoritative evidence → Domain contract → Independent review when warranted → Engineering contract → Implementation → Domain-sensitive validation`

The expert identifies source dates/versions and applicability; separates established
facts, assumptions, approximations and unresolved claims; compares consequential
claims when appropriate; derives equations/algorithms; specifies examples, invariants
and boundary cases; and explains confidence/limits. Missing evidence remains a gap.
Independent domain checking is not a claim of formal proof or regulatory approval.

Domain experts ordinarily produce specifications, not application code. An experiment,
calculation or executable reference model is separately labeled, reproducible and
isolated; it never becomes production code automatically.

Domain contract example (declarative shape, not implemented schema):

```text
id/version; question; affected requirements; sources/access dates;
facts/assumptions/approximations/uncertainty; equations or pseudocode;
units and coordinate conventions; valid range/boundary conditions;
precision/tolerances/error behavior; examples and invariants;
validation method/oracle and its independence; limitations;
review evidence; affected components; content digest.
```

The **Domain Integration Engineer** maps this meaning into the existing architecture:
API/data types, units/dimensions, precision/rounding, representation, failures,
dependency budgets, performance and compatibility. The handoff contains a mapping
from each consequential domain requirement to an implementation boundary and test.
No undocumented unit conversion, approximation, or changed constraint is permitted.

Requirements → expert contract → engineering mapping → changed implementation →
observable tests → independent review are linked by stable IDs and digests. Test
expectations should come from independent examples/invariants where possible,
not solely mirror the implementation or reference model.

Change-impact rules activate specialists only when affected behavior may violate
their contracts. A label/formatting edit outside a domain contract does not restart
research. A changed tolerance, algorithm, unit, trust boundary or model assumption
invalidates relevant evidence and requires targeted specialist validation. Material
domain failure blocks completion; the worker cannot waive it as ordinary polish.

Example: a simulation subsystem may need mechanics and numerical-methods contracts,
an integration engineer and an independent scientific reviewer. A button label
change needs none of them. Domain evidence does not automatically authorize code.

## Product and UI design workflow

`User need → Product brief → Journeys/wireframe → Design contract → Architecture/milestone approval → Implementation → Functional + visual/accessibility QA → Human result approval`

Product reasoning establishes outcomes, users and acceptance. Design establishes
information hierarchy, responsive layout, tokens/components, typography, interaction,
motion and accessibility behavior. Use existing design systems before introducing
new ones. Art direction is optional and tied to the actual product goal.

Design contract: relevant screens/states, journeys, layout constraints, tokens,
reused components, interaction and error/loading/empty states, keyboard/focus rules,
responsive targets, motion constraints, visual references and acceptance evidence.
Version consequential decisions; don't require formal artifacts for a tiny edit.

Implementation follows approved contracts. Independent design review is distinct
from generation and engineering. Visual QA uses actual browser/simulator screenshots
and interactions when supported; static code inspection isn't a visual pass.
Accessibility needs appropriate keyboard/semantic checks. Report unavailable tools
and residual risk honestly. Subjective visual preference is separated from testable
behavior; no external design generator is mandatory.

## State, approvals, and recovery

Retain the existing lifecycle and both human approval gates. Add contract/team/skill
selection previews inside design, not an unconditional new bureaucracy stage.
Future rich-state migration must be explicit, backed up, bounded and reversible.
Schema 2 hardening receipts never silently authorize newly introduced actions.

Project memory remains `.architect-dev-team/state.json` plus referenced architecture.
Create contracts/evidence files only when justified; keep summaries compact. Suggested
optional additions: `contracts/<id>.json`, `evidence/<id>.json`, `skills.lock.json`, and
a bounded decision log. No secrets, hidden reasoning, transcripts, or raw telemetry.

Exact subjects distinguish architecture/milestone, changed mandatory policy,
completed snapshot, external installation, external execution, merge and deployment.
An approval envelope references project identity, kind, scope/revision digest,
policy/contract hashes, human evidence, decision and time. No generic “yes” grants
all actions. Current-scope conversational approval remains convenient and sufficient.
External execution also binds the resolved dependency/runtime manifest and exact
activation context. Stage skills outside host discovery; expose them only through
verified host controls, and replace loaded contexts when revocation cannot unload them.

Resume reconciles actual files/index/HEAD, contract/policy hashes, available human
evidence, previous tasks and scoped grants. Unknown or stale evidence prompts the
specific missing decision. Workers are quiesced before snapshots. Interrupted tasks
are reconciled, not relaunched blindly. Compare-and-swap state revisions and a single
writer prevent lost updates in future CLI persistence; snapshots are not atomic.

## Proposed modules (not created)

```text
.agents/skills/architect-dev-team/
  SKILL.md                         # short native router, existing entrypoint
  references/
    architecture.md, approvals.md, delivery.md, project-memory.md
    delegation.md                   # parameterized roles, not a roster
    domain-contracts.md, product-design.md, skill-discovery.md
  assets/                          # small contract/task templates as justified
  registry/index.json              # minimal discovery index only
  registry/skills/<stable-id>.json  # independent metadata records
  scripts/validate.py              # backward-compatible command facade
  scripts/ldt_core/
    state.py, approvals.py, snapshot.py, registry.py, contracts.py
src/ldt_cli/
  main.py, views.py, storage.py, adapters/
tests/                             # deterministic, integration, scenario replay
pyproject.toml                     # optional CLI packaging, not skill prerequisite
```

The core lives once in the self-contained skill. CLI packaging includes that exact
source through explicit package mapping; it must not maintain a second copy of gate
semantics. Wheel/skill core hashes and schema support are tested together. Split
modules only as their concrete implementations justify it; no empty department files.

## Quality, cost and evaluation

Mandatory policy comes from the approved milestone and affected contracts. Risk-based
checks include correctness, architecture, integration, security, accessibility,
domain precision/performance, docs and explicit unavailable-check dispositions.
Implementers don't certify their own consequential findings or independent review.

Compare plain Codex, hardened V1 and V2 on identical fixture revisions, acceptance,
tool permissions and effort budgets. Include a small edit, existing legacy repo,
cross-component feature, domain-sensitive feature, UI task, and failed/resumed work.
Use multiple runs when judging stochastic behavior; don't attribute a single lucky
run to workflow superiority. Plain Codex is not forced through V2's team policy.

Record available agent count, wall time, delegated task/context size, actual token
telemetry, interactions, review cycles, prevented/escaped defects, test outcomes,
architecture/approval correctness, source-evidence completeness, shortlist relevance,
and CLI completion/cancellation errors. Label unavailable metrics; character/line
counts are proxies. Operational defects and subjective visual ratings stay separate.
No quality, cost, or speed improvement is claimed by this proposal.

## Incremental roadmap and approval boundaries

Every milestone needs its own concrete scope, mandatory policy, tests, independent
review when justified, local/PR evidence, and explicit result approval before the next.

| Order | Small deliverable | Acceptance and evidence |
| --- | --- | --- |
| M1a | Extract the existing deterministic helper into one canonical core | Preserve command/JSON/error and schema compatibility; all 50 current regressions retain outcomes; import/facade checks and independent review; no CLI, installer, new schema or dependency |
| M1b / ecosystem A | Registry schema/source verification for a small catalog | Small pinned catalog, alias/license/unknown evidence tests; old registry migration never promotes trust; no installation/execution; packaging parity before any future CLI distribution |
| M2 | Parameterized roles and domain/product contracts in native Codex | Tiny edit stays Lean; one domain fixture and one product/UI fixture produce linked contracts, impact checks and separate reviewer evidence; no nominal agent roster |
| M3 / ecosystem B–C | Project relevance and native shortlist/consent | Stack-aware 3–5 item shortlist; unrelated/fork/unsupported candidates excluded or explained; selection never installs or grants execution; German/English interaction tests |
| M4 / ecosystem D | Optional CLI status/approvals/skill browser | Plain text/JSON parity, arrow/Enter/Space/Escape behavior, cancel-no-write tests, stale digest refusal, cross-platform test matrix; manual runtime handoff works |
| M5 / ecosystem E | Authorized install/activation adapter for one reviewed source type | Exact preview/execution closure, inert staging outside discovery, verified host isolation/revocation, distinct grants, hash verification, no overwrite, rollback, no remote installer execution; changed artifacts/scope denied |
| M6 / ecosystem F | Compatibility/conflict analysis and bounded bundles | Actual runtime smoke evidence, no competing orchestrators, smallest useful combinations; independent implementation/review/bundle failure tests |
| M7 / ecosystem G | Update maintenance, comparisons and optional richer runtime adapter pilot | New revisions/permissions invalidate relevant consent/review; replayable benchmarks; authenticated supported runtime without fabricated subagent APIs; no automatic publish/merge/deploy |

The first proposed implementation authorization is M1a only: move existing logic
into justified modules under `scripts/ldt_core/`, preserve `validate.py` as its
backward-compatible facade, update affected package references/tests, and obtain
separate review. Its required checks are the existing regression suite, official
metadata validation, package/registry/template validation, command/import parity,
and independent review. A passing check cannot be inferred from module existence.
M1a adds no V2 behavior or runtime dependency. Stop at its result approval before
M1b. Architecture approval does not authorize all milestones, dependencies, service
access, installation, or remote writes.

## Tradeoffs, uncertainty and decision requested

- Mandatory human decisions add interaction cost; minimize repeated questions by
  binding and reusing exact existing approval, not weakening gates.
- Domain and visual expertise improve coverage only if evidence/review is useful;
  no specialist or model can guarantee scientific correctness or taste.
- Fail-closed unsupported filesystem cases reduce automation; manual evidence is
  a disclosed fallback, not a passing snapshot. Recursive submodule attestation is deferred.
- Registry verification needs maintenance and license/permission review. A broad
  research inventory is not a broad activated catalog.
- CLI packaging/runtime APIs, OS permissions, browser/simulator availability,
  terminal accessibility and actual token telemetry need implementation-time checks.
- Local state/receipts are not tamper-proof. Strong protected execution requires
  an external authority/CI boundary, not another instruction paragraph.

**Requested decision:** approve or revise revision 1's boundaries and staged
roadmap and M1a's exact bounded scope/check policy above. V2 implementation is blocked
pending that decision. No CLI, Skill Manager, new roles, or installation adapters
have been implemented by producing this proposal.

The [proposal manifest](v2-proposal-manifest.json) records the reviewed files and
M1a subject with SHA256 digests for this decision packet. Its checksum detects
changes; it is not an approval record or proof of human identity.
