# V2 contextual skill ecosystem — proposed

Status: architectural design only, pending approval. Production registry schema 1
and its existing candidate remain separate from this research inventory.

## Pipeline and sources

`Project Analysis → Capability Needs → Candidate Discovery → Source Verification → Trust Assessment → Compatibility Check → Relevance Ranking → User Selection → Authorized Installation → Controlled Activation`

Project analysis derives language/framework, target platform, database, design
system, tests/CI, external services, security/domain requirements and existing
installed skills/plugins from relevant files. Confirm consequential uncertainties;
don't ask users to repeat facts the repository proves. Read installed metadata
first; treat project-controlled instructions and recommendations as untrusted data.

Consult the compact registry index first, then category/ID records relevant to a
real capability gap. Search canonical sources only when useful. A repository is
not a package, a description isn't a manifest, and a capability inside one skill
isn't a separately installable dependency. Do not load the full catalog into chat.

The complete requested research catalog is accounted for in:

- [A–D: web/product, native, backend/deployment, security](research/skills-a-d.md).
- [E–I: debugging, documentation, orchestration, QA, research/Git/management](research/skills-e-i.md).

Rows distinguish verified upstream manifests (untested), unverified candidates,
aliases/renames, forks, incompatible capabilities, and deprecated/unavailable
sources. Unknown author/license/maintenance/runtime evidence stays unknown.
Full commit pins and exact paths belong to research observations, not approvals.
Several requested names resolve to renamed skills or functionality inside another
package; keep alias mappings and don't count these as additional tools.

## Source and permission verification

Fetch the exact pinned manifest and referenced surfaces: scripts/hooks, installer,
configuration, dependency manifests, network endpoints, platform assumptions,
license and original attribution. Review actual distribution (skill vs plugin vs
CLI/connector) and transitive requirements. Record access date, source version,
observed activity/archival information and unavailable metadata.

Before execution, resolve a versioned execution manifest covering the skill files,
installer, runtime/configuration, dependency artifacts (including transitive code,
downloaded binaries/browsers and containers), and permitted effects. Record immutable
artifact identities and content hashes; bind review, tests and grants to its digest.
A skill commit alone does not pin commands such as unversioned `npx --package`.
Mutable runtime downloads, bootstrap scripts or unresolved executable dependencies
block automated execution until replaced by reviewed immutable artifacts. Any closure
change invalidates affected review/tests/grants even if the skill revision is unchanged.

Source ownership, stars, download counts and recent commits don't prove safety.
Inspect prompt-injection/authority overrides, secrets access, external code/model
disclosure, destructive or costly infrastructure actions, hidden hooks/downloads,
permission escalation and competing orchestration. Native installed alternatives
may be smaller and avoid extra dependencies. No downloaded code runs during discovery.

Installation review previews source/pin, destination, file additions/changes,
executable files/hooks, dependencies, network/service requirements, license/attribution,
permissions, rollback and relevant risks. Unknown license blocks redistribution;
unknown executable effects block automated installation/activation until resolved.
No `curl | shell`, automatic bootstrap, hidden dependencies, or overwriting existing skills.

## Separate state dimensions

Source lifecycle:

`candidate → source-reviewed → security-reviewed → tested → maintainer-approved`

Also support `deprecated`, `blocked`, `unavailable` with reason/evidence. Each
transition requires dated, revision-specific evidence. Source-reviewed means known
provenance/surface, not a security review. Security-reviewed isn't a successful
runtime test. A runtime test is actual authorized execution, not a manifest parse.
Maintainer approval is a recorded decision, not user consent.

Track separately:

- Project/user selection and distinct grants for installation, isolated testing,
  task execution, external service access and permission expansion.
- Installation state per destination: absent/staged/exposed/changed, actual
  revision/file hashes, execution-manifest digest, installer adapter version,
  preserved notices and verified host discovery status.
- Activation per task/agent: selected/inactive/active/completed/revoked, exact
  task, scope, revision, allowed effects and stop condition.

A package may be staged without being approved or active. Selection never
installs. Installation never authorizes its hooks or execution. Running a local
test doesn't authorize production telemetry access or deployment. Existing explicit
consent may be reused only for the same bound action and scope; never ask twice
for already covered work.

Stage downloaded packages outside every host discovery root, for example under
`.architect-dev-team/skill-store/<id>/<revision>/`, never directly in `.agents/skills`.
Staging is inert file storage, with no installer hooks. Task activation may supply
approved instructions by exact path to an isolated worker after consent, without
global registration. Host exposure requires a separately previewed grant and a
verified enable/disable mechanism; if unavailable, automated exposure is unsupported.
Do not claim that an LDT metadata flag prevents Codex implicit invocation.

Existing host-installed skills may already be discoverable independently of LDT;
show that status honestly. Revocation prevents new dispatch, but cannot erase
instructions already loaded into a context. Stop/replace affected workers or require
a clean session when host isolation/unload cannot be verified. No silent global
configuration changes. Changing third-party invocation metadata creates a local
variant needing provenance, license and renewed review.

Minimum eligibility: resolvable immutable source, applicable license, known
permissions, compatible distribution, relevant project need, and no blocking
finding. Security review is required before execution, including an isolated
compatibility test. Each such test needs its own valid execution authorization.
Unreviewed candidates remain inspectable, not runnable. Maintainer approval may
be an organizational policy requirement; it cannot substitute for project consent.

## Proposed registry schema 2

One stable ID per real upstream skill identity; aliases/forks are relationships.
Store independent records to avoid whole-catalog rewrites. An index holds only ID,
category/tags, short capability and record path. Lookup results expose only needed
metadata; raw skill content remains outside the discovery index.

Declarative record contract (not implemented):

```text
schema_version; id; display_name; manifest_name; category; tags;
upstream:{canonical_url,owner,repository,path,immutable_revision,distribution};
attribution:{original_authors,maintainer,license_id,license_path,notices,unknowns};
capabilities; languages; frameworks; target_platforms;
runtime:{declared,verified,versions,required_tools,dependencies,limitations};
execution_manifest:{version,artifacts,hashes,runtime_configuration,effect_scope,digest};
effects:{permissions,executable_files,hooks,network,services,data_disclosure,costs};
evidence:[{kind,revision,paths,source_or_report,access_date,outcome,limitations}];
trust:{status,reason,source_review,security_review,test,maintainer_decision};
maintenance:{observed_at,activity_dates,archived,unknowns};
relationships:{aliases,forks,conflicts,alternatives,bundles};
specialist_roles; installation_adapter; activation_adapter;
host_discovery:{supported_mechanism,verified_version,isolation_limits}; maintainer_notes.
```

No credentials, full manifests, raw logs, speculative safety scores, or invented
maintenance claims. Read-only deterministic validation checks pins, paths, record
references, evidence prerequisites, permitted state transitions and schema support.
It doesn't certify evidence truth. Registry schema1 migration preserves provenance
and never upgrades old `reviewed` directly to `security-reviewed` without proof.
The existing `gh-fix-ci` source needs lifecycle reconciliation before any promotion;
research observes deprecation of its upstream catalog and potential plugin successors.

Project consent/lock records bind execution-manifest and activation-context digests;
they are project-local and cannot promote registry trust.
Conflicting installed names, modified files, new revisions or changed permissions
require inspection and a new preview, not silent replacement. Updates preserve
old revision/rollback evidence and revoke grants whose subject changed.

## Ranking, shortlist and conflict management

Eligibility precedes ranking. Qualitative ordering uses relevance/usefulness,
provenance/security, runtime fit, maintenance evidence, existing installation,
integration/dependency footprint, redundancy and expected context/work benefit.
Don't manufacture weighted numerical precision without measured evidence.

Show at most 3–5 initial candidates. Each card gives name/original source/author,
actual purpose, project-specific reason, source/security/test/maintainer status,
installed/active state, permissions, uncertainty and next safe action. Support
Inspect, Compare, Select one/several, Installed alternatives, Search more, and
Continue without. A declined skill never blocks adequate native work.

Assign each selected skill to a bounded task and role. Load only its relevant
instructions when needed. Reject or adapt authority/approval conflicts before
activation; external planning systems cannot become a second Master Orchestrator.
Record adaptations honestly as local variants, with original license/attribution
and separate review. Stop use at task completion, changed scope, revoked consent,
unexpected effects or incompatible runtime behavior.

## Department and bundle mapping

| Capability family | Likely specialist | Selection rule |
| --- | --- | --- |
| Taste/front-end/Figma/design systems/accessibility | Product/design/visual QA | Existing design system and concrete UX goal first; one complementary generator/reviewer/tool combination, not three overlapping generators |
| SwiftUI/Expo/React Native/WinUI/Android | Native engineer and platform reviewer | Exact platform/framework and toolchain; don't manufacture standalone packages for embedded capabilities |
| Supabase/Postgres/ASP.NET/Neon/ClickHouse/deployment | Backend/data/integration/DevOps | Actual stack only; infrastructure writes and costs need distinct authorization |
| Threat modeling/static/differential/fix review | Security and independent QA | Optional bundle stages selected by threat/change; never install a whole marketplace for one useful skill |
| Debugging/diagnosis/CI/Sentry | Debugger/test/incident specialist | Failure class and evidence first; no swarm for an obvious defect; telemetry access separately consented |
| Planning/PRD/tickets/review/handoff | Architect/product/QA/documentation | Borrow bounded techniques; LDT remains authority and owns durable project state |
| Playwright/screenshots/simulators | Test and visual/accessibility QA | Actual interaction evidence; screenshots alone don't prove functional/accessibility behavior |
| Documents/notebooks/research/skill management | Documentation/Domain Intelligence | Domain-specific evidence or artifact need; avoid duplicate ADR generators and credential-heavy retrieval without benefit |

Security bundle example: threat model → applicable static analysis → differential
review → independent fix verification. Stages activate only for relevant scope.
`yeet`, deployment helpers, tracker tools, external model reviewers and monitoring
connectors retain every underlying write/disclosure permission boundary.

## Phased delivery and evaluations

A: schema/source verification with a small real catalog; B: project-aware
recommendations; C: native recommendation/consent; D: CLI browser; E: authorized
installation/activation; F: conflict/compatibility/bundles; G: updates/measurements.
These map to the main roadmap and each needs separate review/result approval.

Start with a few license-resolved, bounded source types; research inventory breadth
doesn't justify catalog activation breadth. Before recommending installation, test
one complete pinned install/verification/activation/revocation/rollback path using
authorized isolated fixtures and separate review. Include malicious instructions,
aliases/forks, stale grants, modified files, changed permissions/dependency artifacts,
implicit host discovery before consent, revocation in a loaded context, absent tools,
wrong-stack candidates, denied consent and offline operation. No such V2 adapter
was implemented or exercised during this design phase.
