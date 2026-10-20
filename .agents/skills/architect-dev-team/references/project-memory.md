# Durable state and resume

Reuse equivalent repository documents when practical. Default:

```text
.architect-dev-team/state.json       # active scope, checks, pending decision
.architect-dev-team/architecture.md  # saved current versioned proposal
.architect-dev-team/review.json      # latest source snapshot
```

Use [state.template.json](../assets/state.template.json) and selectively adapt
[architecture.template.md](../assets/architecture.template.md). Never overwrite
existing state without reconciliation. ADRs follow project conventions.
Keep state under 64 KiB, normally a few KiB. Retain recent milestone summaries and
current evidence; archive older details in normal project history. Store facts,
not logs, secrets, private reasoning, or unnecessary personal information.

## Read-only commands

`<validator>` is this skill's absolute `scripts/validate.py` path. Quote paths with
spaces. Commands print output; write state/artifact files separately with safe
filesystem tools. Save JSON as UTF-8 without a BOM; don't use shell redirection
defaults that may write UTF-16. CLI output is UTF-8. Python standard library only;
no network or installation. The helper requires Python 3.10 or newer.

The command path remains `scripts/validate.py`. Its parser/output adapter calls
the single implementation in adjacent `scripts/ldt_core/`; copy the complete
skill, not the facade alone. Embedders can import the exported validation functions
from `ldt_core` when the skill's scripts directory is on their import path. Existing
file-path imports of `validate.py` also work without changing the caller's import
path, working directory or streams. File-path imports of different skill copies
keep separate core namespaces, so their validation rules and exception identities
cannot silently mix. Normal `import ldt_core` follows Python's usual module-cache
semantics. Calling `main()` retains the existing UTF-8 console configuration.

```text
python <validator> package <skill-directory>
python <validator> registry <registry-json>
python <validator> registry <legacy-registry-json> --migration-proposal
python <validator> digest <architecture-file>
python <validator> scope <state-json>
python <validator> snapshot <project-root>
python <validator> state <state-json> --root <project-root> [--gate implement|review|advance]
python <validator> migrate-state <legacy-state-json> --root <project-root> --required-check <stable-name>
```

Registry Schema 2 is separate from project-state/snapshot schema numbering.
Its [index, metadata and read-only migration contract](registry.md) does not
change approval semantics or authorize installation/execution.

For bounded read-only technology discovery, see the [inventory API](inventory.md).
Its observations/inferences and coverage gaps are discovery inputs, never approval
evidence or permission to execute a project or an installed skill.

Artifact paths are relative to explicit project root: regular files, no traversal
or symlinks. Without Python, check manually and disclose unavailable automation.

## State contract (schema version 2)

`phase` uses the lifecycle enum; APPROVAL requires `approval_stage` architecture or
iteration, otherwise null. `profile` is lean, balanced, or rigorous.

- `architecture`: null initially, then `{path, sha256}` of saved proposal bytes.
- `milestone`: null initially, then `{id, summary, acceptance: [criteria],
  required_checks: [stable check names]}`. Names are unique; approve the policy
  before implementation. Results must contain each approved name as required.
- `approvals`: ordered `{kind, decision, scope_sha256, review_sha256, evidence,
  recorded_at}`. Kind: architecture/start/iteration; decision: approved/rejected.
  Evidence references the actual human decision. ISO8601 timestamps include timezone.
  Architecture and start decisions have a null review digest; iteration binds the
  snapshot. Scope fingerprints bind architecture, the complete milestone, and the
  profile, so changing review effort cannot silently reuse a prior approval.
  A `start` decision additionally requires a current architecture approval and
  uses the same scope fingerprint; it is an extra gate, not a second state
  machine.
- `checks`: `{name, required, status, evidence, waiver}`. Status:
  passed/failed/not_run/unavailable/waived. Waiver: null or
  `{evidence, reason, scope_sha256}` bound to this exact approved scope
  referencing explicit human disposition. Passed/failed evidence is observed,
  not a planned command. Optional failures remain reportable.
- `review`: null initially, then `{path, sha256, independence, evidence}`, plus an
  optional `verification` block `{path, sha256}` that binds the review to a
  hash-checked runtime evidence artifact. Independence: independent/self/unavailable.
  Reference actual reviewer findings; snapshot validation isn't code review.
  Rigorous gates accept actual independent review only with the bound runtime
  evidence: two distinct verifiable sessions and a read-only reviewer agent.
  A self-declared independence string is not sufficient. Its waiver fallback needs
  `independent_review` in the approved mandatory policy plus a scope-bound human
  waiver. Other proposal-specific review requirements must also be represented by
  approved mandatory check names.
- `completed`, `open_issues`, `constraints`: compact factual string lists.
- Optional M2 fields, absent or null in a pre-M2 state: `brief`,
  `research_results`, `task_contracts`, `project_view`, `pair_results`,
  `lead_session`, `arch_lead_session`, `effort`. A state carrying any of these
  is still schema 2 and validates with the same gates. Unknown fields are
  rejected. `task_contracts` records the contracts that exist; the start gate
  also looks at the contract files on disk, so it fails closed.
- `next_action`: one specific next step or pending human decision.

## Review snapshots

Stop workers after verification/review and final authorized commits. Run `snapshot
ROOT`; save exact JSON as `.architect-dev-team/review.json`, digest it, and set
`state.review`. It lists source paths/hashes and Git HEAD. State validation compares
it to a fresh snapshot, detecting added/deleted/modified files, relevant executable
metadata, staged index changes, and HEAD changes. Snapshot schema version is 2.

Each entry records `type: regular`, content hash, POSIX `executable_bits` (the
three execute bits), and `git_index` metadata when tracked (mode, blob, stage).
Tracked files missing from the worktree use `type: missing` with null content hash
and execute bits, retaining index metadata so staged changes remain visible.
On Windows, filesystem execute bits are null because they are not POSIX permission
semantics; Git index executable modes are still compared. Don't invent a Windows
execute bit from file extensions. Capture source/index metadata after relevant
staging and commits; it remains separate from remote PR verification.

Git enumeration includes tracked and nonignored untracked files. Without Git,
walk exclusions are `.git`, `.architect-dev-team`, `__pycache__`, `node_modules`,
`.venv`, `venv`, `dist`, `build`. Git mode also excludes managed state and
`__pycache__`. Architecture under managed state is hashed separately. Keep the
snapshot under the excluded managed directory to avoid hashing itself.

Directory enumeration errors and Git inventory warnings stop snapshot creation
with diagnostics; a zero Git exit status alone does not establish completeness. Do
not accept a partial manifest. Gitlinks (initialized or uninitialized submodules)
and unresolved index stages are detected explicitly and stop automatic snapshots.
V1 does not recursively attest submodule contents. Resolve conflicts or use an
explicit human-approved manual plan covering gitlink revisions, local submodule
HEADs, dirty/untracked/nested content, and relevant tests. Report automatic gates
as unavailable. Adding a passing check does not make a partial snapshot valid.

Non-UTF-8 filesystem names are rejected with a lossless escaped diagnostic. Rename
them through an explicit filesystem operation or use a disclosed manual plan;
never replace undecodable bytes, normalize them silently, or omit the entry.

Ignored files, external services, remote PR metadata, and generated output aren't
a complete deployment attestation. If excluded content matters, record a meaningful
mandatory check or use an external process. Unrelated
source changes can conservatively invalidate review; refresh instead of hiding
them. Symlinked source is rejected; disclose unavailable automation for such
projects. Snapshot reads aren't atomic; don't edit concurrently.

## Resume and advancement

Read state, referenced design, working-tree status, revision, and human evidence.
Validate and reconcile changed files, incomplete work, and check freshness before
continuing. Phase alone isn't proof. Stale review requires affected checks/review;
changed architecture needs new approval. If human evidence is inaccessible,
confirm the saved scope rather than pretending it was authenticated.

For repair/source drift, preserve the prior revision/failure summary, then clear
the stale review and reset affected checks to `not_run` with null `waiver`;
preserve old waiver dispositions in history. Use phase IMPLEMENTATION
with null approval_stage and validate `--gate implement` before repair. See
[approval recovery](approvals.md). Don't attempt the review/advance gate with an
obsolete snapshot. Rigorous review needs actual independence or the explicitly
waived mandatory `independent_review` check described there.

Validate the old milestone with `--gate advance` before summarizing it in
`completed`. Only then select the next milestone and clear checks/review. Bounded
old decision history can't approve a different milestone.

## Explicit legacy migration

Preserve the original schema 1 JSON and referenced evidence. Legacy `scope`
retains its original fingerprint algorithm. Structurally readable legacy records
with an effective implementation/review/advance phase still refuse automated
gates with a migration diagnostic; do not downgrade the phase to claim authorization.

Derive stable required check names from the saved approved proposal and confirm
uncertainties with the user. Never infer policy solely from mutable result flags.
Run `migrate-state` with one repeated `--required-check NAME` per mandatory check.
It emits JSON only; safely save that output to a new file before replacing state.
An initial state without a milestone needs no required-check arguments.

Migration retains old decisions as history, summarizes old review/check/waiver
evidence in `completed`, clears current review and waivers, resets results, and
returns a concrete scope to architecture approval. Inspect any explicit truncation
notice and retain full original evidence. It never transfers old approval to the
new scope. Reapprove policy/scope, rerun required checks, capture a schema 2
snapshot, and obtain iteration approval before advancement. No automatic migration
or hidden reapproval occurs.
