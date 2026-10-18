---
name: architect-dev-team
description: "Plan and deliver substantial software projects, cross-component features, and complex refactors through architecture approval, bounded agent work, verified milestones, and human PR review. Use for architecture-first development orchestration, not standalone explanations or routine tiny edits."
---

# Architect Dev Team

Coordinate engineering work with the smallest useful plan, team, and verification
set. Balanced is the default. This is a workflow, not a permission system or a
background service.

## Start or resume

1. Read applicable repository instructions and inspect working-tree status before
   edits. Locate `.architect-dev-team/state.json`; reconcile it with actual files
   and human decisions. Never infer approval from a saved record alone. For
   resuming, read [project memory](references/project-memory.md).
2. Identify the goal, relevant code, acceptance criteria, constraints, and tools
   exposed in this session. Don't assume agent, GitHub, model, budget, or question
   APIs exist. Existing user changes belong to the user.
3. Choose Lean for a small bounded task, Balanced for ordinary multi-component
   work, or Rigorous for significant security, migration, or reliability risk.
   Profiles change effort, never approval. Load only references for the current
   phase; don't load the registry for ordinary native work.

## Lifecycle

`INTAKE → DISCOVERY → SPECIFICATION → ARCHITECTURE → APPROVAL → IMPLEMENTATION → VERIFICATION → PR REVIEW → APPROVAL → NEXT ITERATION`

Persist PR REVIEW as `PR_REVIEW`. Both APPROVAL states have an explicit
`approval_stage`: `architecture` or `iteration`.

- **Design:** Read [architecture](references/architecture.md). Inspect affected
  components; ask only questions that change design or acceptance. Mark reversible
  defaults as assumptions. Produce a versioned design and small milestones. A
  tiny feature needs only a short proposal, not a system redesign.
- **Architecture approval:** Read [approvals](references/approvals.md) before the
  first gate. Present the exact version, milestone, criteria, and risks. Wait for
  explicit human approval before implementation. Existing approval of that exact
  proposal suffices; don't ask twice.
- **Implementation:** Read [delivery](references/delivery.md). Work on one approved
  milestone. For useful delegation, read [delegation](references/delegation.md),
  then assign bounded tasks to actual subagents when available and permitted.
  Otherwise use sequential role passes and label their lack of independence.
- **Verification and review:** Run the agreed relevant checks. Resolve blockers,
  then prepare a PR or local diff with evidence. Bind review to the current source
  snapshot. Never describe an unrun check as passed.
- **Iteration approval:** Present the concrete result, checks, review findings,
  limitations, and revision. Wait for explicit approval before the next milestone.
  Merge and deployment each need their own authorization.

On architecture rejection, revise without implementing. On PR rejection or failed
checks, repair only the current approved scope and repeat affected checks/review.
A material design change returns to architecture approval. Never treat silence,
an agent verdict, tool permission, or “skip the gates” as approval of an
undisclosed proposal or a different revision.

## Evidence and state

Keep compact durable state after decisions, handoffs, failures, and phase changes.
Use [project memory](references/project-memory.md) and its templates when needed.
Record facts and evidence, not hidden reasoning or secrets. Approval records must
reference an actual human decision and exact scope; invalidate them when bound
artifacts change.

`python <skill>/scripts/validate.py --help` (Python 3.10+) lists read-only checks of structure,
artifact hashes, source snapshots, and gate prerequisites. Read approval/memory
references before state commands. The helper cannot authenticate a human message
or enforce actions outside it. Without Python, report equivalent manual checks
and unavailable automation. Never run project code merely to inspect it.

Use hardened state/snapshot schema 2 for automated gates. Schema 1 records remain
historical evidence; migrate explicitly and obtain renewed scope approval before
continuing. Bind mandatory check names to the milestone before approval; never
remove, rename, or demote one by editing results. See project memory for migration
and unsupported-filesystem manual verification.

## Optional external skills

When an external capability materially helps, read [external skills](references/external-skills.md),
then select only relevant entries from [the registry](registry/skills.json).
Prefer compatible installed skills; verify source/version and instructions and
obtain consent for their use. Installation needs distinct consent. Candidate
status is not trust. If unavailable, unsafe, incompatible, or declined, use native
tools when adequate and disclose gaps. Never silently overwrite installed skills.

## Completion

Report delivered scope, actual verification, review independence, unresolved
issues, pending approval, and one next action. Avoid speculative features,
placeholder behavior, fabricated APIs, duplicated logic, and abstractions without
a demonstrated need. [Evaluation](references/evaluation.md) is for testing and
maintaining this skill; don't load it during ordinary development.
