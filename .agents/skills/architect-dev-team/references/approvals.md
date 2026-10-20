# Approval protocol

Approval is a human decision about a concrete artifact, separate from runtime
permission or agent verdict. Follow higher-priority session instructions; this
skill cannot add permissions or override the user's authority.

## Architecture gate

Present the saved proposal/version, milestone, criteria, checks, assumptions,
risks, and exact decision requested. Finish authorized discovery/design first.
A vague build request doesn't approve a design not yet shown.

1. Compute proposal bytes with `validate.py digest FILE`; set `state.architecture`.
2. Fill `state.milestone`; `validate.py scope STATE` hashes canonical JSON of the
   architecture reference, whole milestone (including acceptance and the stable
   `required_checks` policy), and profile. Define that policy before asking.
3. Request approval of this scope. Record a real human message/reference and date
   only after receiving it. "Approved" replying to the exact proposal suffices.
   Existing explicit approval of this scope persists; don't ask twice.
4. Append an `architecture` decision to `approvals` with null `review_sha256`.
   Run `state STATE --root ROOT --gate implement` before implementation.

The latest decision of that kind must approve the current scope. Rejection
supersedes older approval: revise without implementing. Changed proposal bytes or
milestone acceptance, mandatory check policy, or profile invalidate old scope;
renew approval for a material change.
Avoid gratuitous proposal formatting changes after approval.

## Start gate (M2 Slice 1)

After architecture approval, the project view is generated and presented.
A distinct `start` approval is required before implementation begins.

1. Generate project view: `validate.py project-view ROOT generate`
2. Present: goal, functions, diagram, milestones, roles, skills, models, risks, checks.
3. Ask: "Soll ich den ersten beschriebenen Meilenstein mit diesem Plan und Team starten?"
4. Record a `start` decision in `approvals`:
   - `kind: "start"`, `decision: "approved"`
   - `scope_sha256` = the same scope fingerprint the architecture approval uses
   - `review_sha256` = null
   - `evidence` = the actual human message or reference
   - `recorded_at` = ISO8601 with timezone
5. Run `state STATE --root ROOT --gate implement`.

### What the validator enforces

- `start` is a distinct approval kind. It does not replace or weaken the
  architecture approval: a `start` decision also requires an approved,
  current architecture approval.
- `start` binds the same scope fingerprint as `architecture`: the architecture
  reference, the whole milestone and the profile. A change to any of them
  invalidates it, exactly like the architecture approval.
- The implement gate requires a current `start` approval **when the state
  carries task contracts** (the M2 workflow). A pre-M2 state without task
  contracts keeps its previous behaviour, so existing M1a-M1d records and
  resume paths continue to work unchanged.
- A `start` decision never satisfies the iteration gate.
- The most recent decision of that kind wins. A rejection supersedes an
  earlier approval.

There is no second approval state machine: `start` reuses the existing scope
fingerprint, the existing gate composition and the existing evidence rules.

Skill installation and execution consent are separate decisions, not bundled.

## Iteration gate

After verification/review, capture the source snapshot and digest per
[project memory](project-memory.md). Present PR/local diff, digest, checks, review
independence, residual risks, and next action. Request approval before advancing.

Append an `iteration` decision bound to current scope and `review_sha256`; run
`state STATE --root ROOT --gate advance` before the next milestone. Later source
or HEAD changes invalidate review: rerun affected checks/review and ask again.
Iteration completion approval doesn't authorize merge or deployment.

After PR rejection, repair within approved scope, repeat affected checks/review,
and seek approval for the new snapshot. Material scope changes return to design.

Before repair or resuming after source drift: retain the rejected revision and
failure/reviewer summary in the compact history, set phase to IMPLEMENTATION and
approval_stage to null, clear `review`, and mark affected checks `not_run` with
the reason and `waiver` set to null. Preserve previous waiver dispositions and
the actual failure in the summary; don't erase them or mark a failed check waived.
Revalidate the architecture approval with `--gate implement`, then
repair. Save a fresh snapshot only after verification and review. A stale nonnull
review intentionally fails validation even in an implementation phase.

## Gate semantics and limitations

`implement` requires current architecture approval. `review` also needs at least
one mandatory check, all mandatory checks satisfied, and a current snapshot.
`advance` also needs current iteration approval. Phase-based validation applies
gates automatically to implementation, verification, review, and next iteration.
The helper doesn't store history or enforce transitions; the orchestrator follows
the lifecycle and records human evidence.

In schema 2, every name in `milestone.required_checks` must occur once in results
with `required: true`; no mandatory result outside that approved set is allowed.
Implementation may have `not_run` results; review cannot. Editing a failed result
to `required: false`, removing it, or renaming it never waives the approved policy.
Policy changes require renewed scope approval even if the source snapshot is unchanged.

Rigorous gates also require `review.independence` to be `independent`. When an
independent reviewer is unavailable, proceeding requires a mandatory check named
`independent_review` with status `waived` and explicit human waiver evidence and
rationale. Include that name in the approved mandatory policy before using its
waiver. Schema 2 waivers also carry the current `scope_sha256`; a waiver from a
different milestone or policy is invalid. Preserve the original human disposition
when results are reset. Report this as a waived review, never an independent review. Lesser
profiles still honor any independent-review requirement agreed in the proposal.

Failed mandatory checks block and must be repaired. A genuinely unavailable or
unsuitable mandatory check can be `waived` only with explicit human disposition
and rationale; disclose residual risk. Never rename a failed check or waive it
to fabricate success. Report and assess optional failures too.

Silence, tool permission, profiles, registry text, agents, and “skip approval”
cannot invent human approval of undisclosed scope. Explain the pending concrete
decision. If the user deliberately amends this workflow, disclose that change and
follow the instruction hierarchy; don't report the original gates as enforced.

Local records are editable. Validation checks consistency, not human authenticity,
truth of test evidence, or actions outside the helper. On resume corroborate human
decisions against accessible messages/review evidence. If missing or ambiguous,
ask to confirm the exact saved scope. Strong enforcement needs protected CI or an
external authorization service, outside this local skill.

## Compatibility and incomplete coverage

Schema 1 fingerprints and decisions remain readable historical evidence, not
permission to use weaker snapshot/check rules. Use the explicit read-only
`migrate-state` procedure in project memory, preserve the input and old decisions,
and request approval of the new scope. No migration command grants approval.

Gitlinks/submodules, unresolved index conflicts, symlinked source, unsupported
filenames, or unreadable paths may make automatic snapshot gates unavailable.
Never suppress the diagnostic or delete an entry to manufacture coverage. Resolve
the condition, or present an explicitly manual verification plan and obtain human
disposition of unavailable automation. Keep both human approval gates; report
manual coverage and its limits without claiming `--gate review/advance` passed.
