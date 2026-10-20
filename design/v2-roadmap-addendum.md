# V2 roadmap addendum — M1d Revision 1

M1d is an approved **documentation-only** reconciliation milestone. This addendum
implements no runtime behavior and authorizes no later milestone. It supplements
the [original architecture](v2-architecture.md), [ecosystem plan](v2-skill-ecosystem.md)
and [future organizational requirements](v2-organizational-requirements.md).
The original proposal files and M2–M7 scopes remain unchanged. Ecosystem phase D
means the later CLI browser; it is not the separately authorized M1d designation.

## Completed foundations and evidence

| Foundation | Implemented interface and evidence | Boundary |
| --- | --- | --- |
| M1a shared core | [Core exports](../.agents/skills/architect-dev-team/scripts/ldt_core/__init__.py), existing `validate.py` facade; [approval protocol](../.agents/skills/architect-dev-team/references/approvals.md) | One implementation of state, scope, snapshot and gate rules; local consistency checks do not authenticate a human decision |
| M1b Trusted Skill Registry | [Registry contract](../.agents/skills/architect-dev-team/references/registry.md): Schema 1 compatibility, read-only Schema 2 index/records and explicit migration proposals | All three records remain untrusted candidates; successful validation is not source authenticity, security review, compatibility or consent |
| M1c project inventory | [Inventory contract](../.agents/skills/architect-dev-team/references/inventory.md), `ldt_core.inventory(root)`, output version 1 | Observations, inferences, generic needs, unknowns and coverage; no recommendation, role allocation or execution |

Completed milestone decisions and raw checks are local evidence, retained outside
Git in `.architect-dev-team/`. Accepted M1c evidence records 108 tests: 103 passed,
five native platform skips. Its existing-repository run observed a Git marker and
installed manifest, inferred Python from a test filename, and left the source
snapshot unchanged. This does not establish runtime compatibility or activation.
The two POSIX and three symlink skips, mocked permission/reparse checks and
Windows/Python 3.12-only execution remain limitations, not passing native coverage.

## Requirements-to-milestones traceability

Every row below describes **future planning**, not an implemented workflow.

| Requirement | Existing roadmap destination | Dependencies and boundary |
| --- | --- | --- |
| Project-aware discovery/recommendations | M3, ecosystem B–C | M1c task-relevant facts/needs plus M1b identity, provenance, license, lifecycle, trust and runtime uncertainty; eligibility precedes ranking; native fallback remains available |
| Master → Department Lead → Specialist | M2 native parameterized roles/contracts | Approved task objective and affected interfaces, actual available agents and bounded ownership; no permanent roster or recursive specialist spawning |
| Department assignment and output validation | M2, including integration and independent QA | Lead checks architecture, missing details, assumptions, dependencies, acceptance and verification before decomposition; reviews/rejects specialist output and returns an integrated result |
| Master authority and resource efficiency | M2 contracts; M7 comparative measurement | Master owns priorities, cross-department integration, resource allocation and approval enforcement; leads request extra specialists and escalate unresolved questions; tiny tasks retain direct Lean work |
| Domain Intelligence and expert allocation | M2 domain/engineering contracts | Explicit domain questions and reviewed authoritative evidence; language/framework signals alone cannot establish domain expertise needs |
| Independent domain validation | M2 acceptance; later changes retain affected-domain review | Separate expert evidence/oracles, assumptions, units, tolerances and uncertainty from engineering mapping and implementation; an implementer cannot supply its own independent certification |
| Professional writing | M2 Content/Technical Writing responsibilities; M3 relevant skill discovery/selection | Audience, purpose, verified facts, outline, draft and accuracy/clarity review; Softaworks preference does not establish source trust or consent |
| Creative website design | M2 product/design contracts; M3 selective skill choices | Visual Design Lead plans two or three distinct concepts, recorded human choice, typography/color/components/interaction/accessibility; engineering follows approved design |
| Complementary skill use | M3 selection; M6 compatibility/conflict/bundles | Different creative, design-system and accessibility/review responsibilities; no indiscriminate overlapping generators or whole-toolkit activation |
| Context and cost discipline | M2 bounded handoffs; M7 measurements/runtime pilot | Pass relevant paths/contracts rather than full chats; record available telemetry and missing metrics; no invented savings or new telemetry system |
| Native shortlist and consent | M3, ecosystem C | Preserve source/trust/install/execution distinctions; a selection never grants execution or installs a skill |
| Optional CLI | M4, ecosystem D | Future views call the same core; no second approval state machine; native Codex remains usable |
| Authorized installation/activation | M5, ecosystem E | Separate exact grants, immutable execution closure, inert staging, host isolation, verification, rollback and revocation; no adapter exists in M1d |
| Compatibility/conflicts/bundles | M6, ecosystem F | Scoped actual runtime evidence and separately authorized execution; source metadata alone cannot prove interoperability |
| Updates and comparisons | M7, ecosystem G | Changed artifacts/permissions invalidate affected evidence/grants; updates do not silently reuse old consent |

M2–M7 retain their original deliverables and order. These mappings identify where
new requirements need detailed proposals; they do not enlarge an approved
implementation scope. The exact first M2 slice, department activation thresholds,
and writing/design contract details remain open decisions for that architecture gate.

## Dependency and consumer contracts

The planned dependency flow is: completed M1a gate/core primitives → M1b metadata
and M1c evidence inputs → separately scoped M2 task/domain/product contracts →
M3 relevance/selection/consent → M4 optional views → M5 authorized adapters →
M6 compatibility/bundles → M7 updates/comparisons. This shows prerequisites and
roadmap order, not an executable pipeline. No edge transfers authorization.

Future inventory consumers must preserve these descriptive contracts:

- **Meaning:** keep `observations`, `inferences`, inferred `capability_needs`,
  `unknowns` and `coverage` distinct. A dependency declaration or filename is a
  signal, not an installed dependency, validated configuration or proven domain.
- **Evidence:** carry safe project-relative paths and signal labels. They may
  expose private identifiers; selected JSON may briefly contain sensitive bytes.
  Do not treat the inventory as a sanitizer or copy arbitrary file contents into
  prompts/logs. Missing evidence is unknown, not evidence of absence.
- **Freshness:** the current API supplies no authenticated project identity,
  timestamp or source snapshot. A future caller must bind context/revision and
  obtain fresh evidence after relevant changes through a separately reviewed
  contract. Deterministic output is not freshness; do not invent new fields now.
- **Coverage:** inventory is always incomplete and allowlisted. Preserve limits,
  skipped paths and errors. Only `package.json` content is parsed; other supported
  configs are presence signals. Do not run config/scripts/Git/network to fill gaps
  automatically. A stable local tree is required; traversal is not atomic against
  a racing writer, and linked/reparse roots are refused.
- **Registry boundary:** query only relevant metadata in future M3 work. Preserve
  canonical identities, aliases, immutable pins, lifecycle, evidence and uncertainty.
  The three existing candidates do not become trusted through migration or use.
  Source/license assertions are not security/runtime verification; unresolved
  licensing or executable effects cannot be silently treated as safe.
- **Authority:** inventory facts are not authorizations; discovery is not trust;
  trust is not installation consent; installation is not execution consent; expert
  recommendations do not authorize agent creation or implementation; architecture
  approval does not authorize merge or deployment. Local hash checks verify
  consistency, not identity or human authenticity.

Future task handoffs should identify objective, architecture revision, boundaries,
inputs/dependencies, expected output, owner, acceptance, verification, compact return
format and escalation conditions. Department leads validate assignments and results,
but cannot override Master allocation or human gates. Specialists do not expand scope
or spawn recursively. Department acceptance, cross-department integration, independent
QA and final human approval remain distinct; a missing reviewer is disclosed.

## Four architecture examples — proposed responses only

These are reasoning examples, not executed agent assignments or feature evaluations.
The comparisons with M1c evidence establish input semantics only.

**1. Small repository, minimal orchestration.** The real M1c repository evaluation
inferred Python from `tests/test_core_equivalence.py`; it did not prove a framework
or expert need. For a hypothetical small label/documentation edit, future M2 would
keep direct Lean work and relevant checks. No department roster, domain researcher
or external skill follows automatically from the Python signal. Installed manifest
presence establishes neither activation nor consent.

**2. Domain-heavy task.** Assume the user requests a numerical model with missing
unit and error-tolerance requirements. Source extensions alone cannot resolve those
questions. Future M2 would first clarify requirements, request a bounded Domain
Intelligence contract, and plan distinct validation of assumptions, units, boundaries
and tolerances. Engineering mapping follows reviewed domain meaning and explicit
architecture approval. Unresolved scientific claims block consequential implementation;
an expert suggestion supplies no resource or implementation grant.

**3. Website task.** Assume a product brief and a declared React dependency, as in
the M1c monorepo fixture. React is an inference from a declaration, not validated
runtime behavior or a design direction. Future M2 would coordinate product goals,
two or three visual concepts and human selection, verified content inputs, writing
review and frontend contracts. The proposed writing discipline prefers Softaworks
`writing-clearly-and-concisely`; `humanizer` is optional and README work may use
`crafting-effective-readmes`. Actual upstream paths, license, immutable revision,
compatibility and relevant consent require separate verification. When external use
is unavailable or unapproved, disclose it and apply native writing checks; request
installation approval only when relevant. Future M3 would consider complementary
creative/system/accessibility skills, not activate a toolkit. Implementation and
browser/keyboard/accessibility review would follow their own approvals and actual
tool availability. The LittleDevTeam website remains a separate project scope.

**4. Incomplete or uncertain inventory.** Assume malformed `package.json`, a
filename-only config signal and unreadable or linked directories, as covered by M1c
fixtures. Future consumers would retain `complete: false`, errors and unknowns,
and distinguish the config filename inference from parsed evidence. They would
seek only task-relevant clarification or stay with adequate native work, never
manufacture a full stack, trusted candidate or department assignment. They would
not execute configuration or follow unsafe paths to make coverage appear complete.

## Next decisions and unchanged approval boundaries

The next existing milestone is **M2: parameterized native roles and domain/product
contracts**. Its original acceptance includes a tiny edit staying Lean, one domain
fixture and one product/UI fixture with linked contracts, impact checks and distinct
review evidence; no nominal roster. A separate M2 proposal must bound its first
slice, owners, contract representation, verification and exact required-check policy.
No M2 implementation or schema choice is approved by M1d completion.

Later M3 proposals may consume inventory and registry metadata for relevance and
native selection, after uncertainty/eligibility and consent rules are specified.
M4–M7 retain their CLI, adapter, compatibility and update/measurement subjects.

These bounded follow-on outlines require separate architecture decisions:

| Outline/objective | Prerequisites | Decisions still required | Exclusions |
| --- | --- | --- | --- |
| M2: first native task/domain/product contract slice | Completed foundations, concrete task and available runtime capabilities | Exact deliverables/representation, file ownership, maximum concurrent specialists and context/output limits, escalation, cancellation/resume after interrupted handoffs, independent acceptance and mandatory checks; obtain human architecture approval | No roster-wide rollout, recommendation engine, CLI, installer or automatic permission inference |
| M3: bounded relevance and native selection slice | M2 contracts, M1c evidence with freshness/coverage, M1b metadata/trust uncertainty | Eligibility/unknown handling, shortlist/decline behavior, exact selection-versus-execution consent contract, supported sources and verification policy; obtain human architecture approval | No installation/activation adapter, department orchestration, CLI or automatic trust promotion |

M2 recovery planning must reconcile actual files, completed/incomplete handoffs,
current contracts and human decisions before resuming; do not blindly respawn work
or reuse stale approval. M4–M7 still need their own later bounded proposals rather
than implementation outlines expanded here.
Every proposal needs its own exact scope, human architecture decision, verified
result and completion approval. Department or expert judgments cannot waive those
gates. M1d changes no API, schema, registry trust, runtime prompt, dependency or
external permission; installation, activation, publication, push, merge and deployment
remain separately authorized actions.
