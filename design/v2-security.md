# V2 security and approval threat model — proposed

Status: design, not a claim of implemented protection. Scope includes the native
skill, shared core, registry/research, optional CLI, runtime adapters and local
installation workflow. No new external service or protected CI was provisioned.

## Assets and boundaries

Protect user source/changes, exact approved architecture/milestones/check policy,
domain/design meaning, verification evidence, credentials/telemetry, installation
destinations, license notices, budgets and external-action authority.

Trust boundaries: human request/decision ↔ orchestrator; repository/remote content
↔ instructions; worker ↔ coordination; registry assertion ↔ source evidence;
CLI rendering ↔ core decision; core ↔ filesystem/runtime; local task ↔ cloud,
tracker, production telemetry, public publication, merge and deployment.

Source files, manifests, search results, citations, issues, test logs and downloaded
instructions are data with differing provenance, not permission grants. A task
result isn't a human decision. Local administrators/editors can alter state; no
local hash chain or self-authored receipt solves that authentication problem.

## Threats and controls

| Threat / concrete trigger | Proposed control | Required evidence / residual risk |
| --- | --- | --- |
| Approval reuse after scope/policy/contracts/profile/source changes | Bind action kind, project, scope/revision and relevant hashes; recompute before action; latest rejection wins | Negative replay/demotion/stale tests; local records still need corroborated human evidence |
| Source drifts between approval, tool dispatch and review | Quiesce workers, compare revisions before/after, preserve user changes, refresh checks/review | Race/cancellation tests; filesystem snapshots aren't atomic |
| Missing files, unreadable subtrees, warnings, gitlinks or unsupported paths create partial coverage | Fail closed with explicit unsupported/manual path and human disposition; never omit to get a green gate | Real/mocked traversal, mode/index/tombstone/gitlink tests; V1 submodule attestation remains manual |
| Malicious skill redefines authority or requests credentials/remote installers | Treat content as untrusted; review full surface at pin; orchestrator resolves conflicts; least-privilege tool/sandbox boundary when actually supported | Injection/exfiltration/hidden-hook fixtures; prompts alone aren't a sandbox |
| Trusted name points to a fork, renamed package, mutable branch or altered install | Canonical identity + full commit + paths/content hashes; verify notice/license and relationships | Alias/fork/name-collision/tamper fixtures; unknown evidence remains unknown |
| Pinned skill invokes changed unversioned dependency code | Resolve/hash the execution manifest including transitive artifacts, installer, runtime/configuration and effects; bind evidence/grants to its digest; unresolved mutable downloads block execution | Same-skill/different-dependency replay tests; closure changes invalidate affected evidence |
| Selection/install mistaken for permission to execute/push/deploy | Distinct typed, scoped grants; execution test consent separate; externally visible effects each need relevant authority | Negative cross-kind authorization tests, denied consent remains pending; no automatic grant promotion |
| Installation exposes implicit instructions before activation, or revocation leaves loaded instructions | Stage outside host discovery; verify host isolation before exposure; use explicit task instructions in isolated workers; stop/replace loaded contexts on revocation | Host-version discovery/revocation tests; metadata flags cannot erase context or control independently installed skills |
| Installer traversal/overwrite or hidden dependency hooks | Exact preview, approved resolved destination, safe file writes, no remote bootstrap execution, transaction/rollback and hash verification | Path/symlink/collision/interruption tests; dependencies themselves need review/permission |
| Worker changes another task's files or certifies its own result | Explicit ownership/allowed effects, independent reviewer on consequential changes, Master integrates/verifies | Collision and self-certification scenarios; a different model isn't a formal proof |
| Domain references/units/precision corrupted during implementation | Hash approved contracts, trace mapping/invariants, independent oracle/domain review where material | Unit/dimensional/numerical boundary and changed-contract tests; source uncertainty persists |
| Terminal metadata/logs inject escape sequences, links or shell syntax | Render escaped/bounded data; argv invocation; explicit cwd; separate display text from action IDs | Control-character/quoting fixtures; no raw secret logs |
| Forged evidence or untrusted user-looking text authorizes action | Corroborate source user message/operator event; do not infer authenticity from files or role-play | Resume-forgery/replay tests; strong authority requires protected external boundary |
| External tools disclose code or access production data/cost money | Explicit service/destination/data scope; isolated test data; redaction and budget limits when supported | Denied telemetry/provider/deploy scenarios; don't switch provider silently |

## Approval model

Retain architecture and iteration approval. Distinguish scope changes, mandatory
policy changes, external installation, external execution, merge and deployment.
Each decision names its exact subject and evidence source. Rejections and revocation
invalidate only their relevant authority; no worker, timeout, setting, registry
status or installer may manufacture approval. Reuse existing exact consent rather
than requesting it repeatedly.

Runtime permission prompts protect execution capabilities; they aren't architecture
approval. Conversely an approved plan doesn't grant unrestricted shell/network or
credentials. CLI adapters must not silently use bypass/auto-approval flags.

Local receipts/history help reconciliation and accidental-corruption detection.
They are advisory under the current OS-user trust boundary. If an organization
needs tamper-resistant approval or protected release enforcement, design a separate
authority/protected CI milestone and threat model; don't imply it exists already.

## Independence, failure and recovery

Implementation and consequential verification use distinct actual reviewers where
supported. Reviewer findings require separate confirmation before certification.
Workers may challenge domain/product assumptions before code. A missing specialist
is disclosed; a self-pass is never labeled independent or formal proof.

Failure stops the affected action. Retain compact evidence and original human
decisions, reset stale results/waivers, reconcile actual effects, and request only
the needed new decision. Never discard user changes, suppress warnings, rerun a
non-idempotent operation blindly, or claim a partial rollback fully succeeded.

## Planned security evaluation

Add tests for each table row to its delivery milestone. Keep malicious archives,
invalid paths, conflicting grants and source/contract changes in synthetic fixtures;
no real credentials/telemetry. Independent security review inspects the final
adapter and installer implementation, not just this document. Until those exist,
the proposed controls aren't validated capabilities.
