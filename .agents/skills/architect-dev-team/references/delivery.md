# Incremental delivery

## One approved milestone

1. Validate current scope approval. Inspect status/user changes and preserve them.
   Select a small implementation unit inside the milestone; every internal task
   doesn't need its own PR.
2. Use an appropriate feature branch; detect the base, don't assume `main`. Avoid
   reset, force push, discarded work, and branch deletion. An unborn repository
   needs an explicit initial baseline. Initialize Git or commit only within task
   authorization. Without Git, keep before/after evidence and disclose limitations.
3. Implement directly or through bounded workers. Stop for a material design delta.
4. Run agreed meaningful checks; record command, outcome, and concise evidence.
   Don't repeat broad suites without changes, failures, or unresolved risk.
5. Review, repair blockers, rerun affected checks, and review the final changes.
   Capture the source snapshot after all code/test changes and authorized commits.
6. Prepare PR/local handoff and request iteration approval. Wait before advancing.

For rejected review or source drift, first preserve the previous findings and
invalidate `review` plus affected check results as described in
[approval recovery](approvals.md). Architecture approval remains usable only for
the same unchanged design and milestone; old iteration approval cannot advance
the repaired revision.

## Quality gates

Choose mandatory checks with the proposal. At least one meaningful required check
is necessary, including a recorded manual acceptance inspection for low-impact
documentation. Avoid tests mirroring implementation or headings.

Bind stable check names in `milestone.required_checks`; changing a result's
`required` flag does not change approved policy. Use scope-bound explicit waivers
only for genuinely unavailable/unsuitable checks, and renew approval for policy
changes. Snapshot failures are unavailable automation, never passing coverage.

| Concern | Mandatory when relevant | Optional expansion |
| --- | --- | --- |
| Correctness | Observable acceptance and affected regressions | Wider suite for shared behavior |
| Types/lint/build | Repository-required checks for touched code | Extra static analysis for concrete concerns |
| Interfaces/data | Contract, integration, migration checks for changed boundaries | Isolated end-to-end smoke run |
| Security/dependencies | Changed auth, trust, secrets, package risks | Authorized specialist assessment |
| UI | Accessibility and observable changed behavior | Broader device/browser coverage |
| Performance/reliability | Evidence for explicit budgets/sensitive paths | Authorized isolated load/fault tests |
| Architecture/docs | Approved boundaries and accurate affected usage | Unrelated cleanup deferred |

Inspect unfamiliar test/config commands before execution; they run project code.
Keep secrets out of logs. Missing dependencies/services mean `unavailable`, not
`passed`. Exit zero isn't enough if no intended tests ran or the wrong target ran.

## Integration & Architecture Conformance (M2 Slice 1)

After task-level reviews, integration combines reviewed results into an executable whole.

**Integration Engineer** (Lead or designated):
- Receives reviewed task results from Department Leads.
- Responsible for: interfaces, error handling, executable whole.
- Uses isolated worktrees or clear file ownership for parallel integration.

**Architecture Lead Review** (after integration):
- Compares: architecture, domain contracts, actual implementation.
- Re-engages research specialists only for NEW domain questions.

**Final Mandatory Tests** (at integrated whole):
- Integration tests
- End-to-end tests
- Security tests (if in scope)
- Performance tests (if budgeted)
- Any other approved `required_checks`

**Review Invalidation**:
- Any integration change affecting previously reviewed code → affected reviews invalidated.
- Re-run affected checks + independent re-review.

## PR or local handoff

Use available GitHub tools only after checking host/repo, access, and existing
authorization for push/PR creation. Don't authenticate or modify remotes silently.
For an authorized PR, record actual base/head, concise problem/result, checks,
review findings, and risks. Don't push unrelated user changes. Preserve newlines
in PR descriptions.

Without tooling, permission, or connectivity, provide local diff, changed/untracked
file inventory, base/HEAD if available, source snapshot, commands/results, review
status, and manual PR steps. Don't claim a remote PR exists. Complete authorized
local work before requesting an external mutation's permission.

A commit after a snapshot changes HEAD: refresh it before approval. Verify remote
PR head matches reviewed local HEAD separately; remote PR metadata isn't covered
by the local snapshot. Reconcile remote changes before relying on local review.

After explicit iteration approval, mark the old milestone complete, then select
the next. Its exact scope needs architecture approval before implementation.
Merge/deploy require separately authorized actions against the reviewed revision;
passing checks and iteration approval don't supply that authority.
