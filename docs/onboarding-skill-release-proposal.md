# Skill onboarding and release proposal

Status: proposal only, 20 October 2026. No skill release is authorized here.

The short Quickstart asks the installing agent to retrieve and verify the skill,
then invoke `$architect-dev-team`. Installation happens before the skill is
available, so the installed skill alone cannot enforce its own bootstrap.

## Distributed capability boundary

Public revision `838a2e1376a0b3e44931c54310be95d253380b1a` carries the same skill
files as reference revision `9a062eb9de0990ce1074dd677d26e5a528ee14a0`.
Its instructions cover inspecting an existing project, clarifying new software,
architecture proposals, bounded specialist delegation when available, external
skill recommendations with consent, verification and durable project memory.
These are agent instructions, not a background service or guaranteed runtime.

The structured intake, architecture-team/task-contract helpers, project view,
pair execution, integration and OpenCode runtime described in the newer website
are absent from that package. They exist in a separate local development scope;
their presence there does not establish release readiness. Automated stable
release selection and installation provenance are also absent. No stable GitHub
release exists at the date above.

## Proposed separate delivery

1. Reconcile and review the existing skill-development work without importing or
   overwriting its milestone state. Decide which helpers belong in a release.
2. Add a concise bootstrap/version policy and route vague or new requests to
   discovery and focused questions. Keep research, specialist selection, external
   skill recommendations, project overview and scoped implementation approval
   inside the skill. Preserve its identifier and existing approval boundaries.
3. Define the installing agent's contract: check current release metadata,
   exclude drafts/prereleases, verify compatibility and package checks, explicitly
   offer a verified development fallback, resolve a full commit at installation
   time, compare existing installs and save provenance outside the package.
   Never classify `main` as stable by default. Network failure is not proof that
   no stable release exists.
4. Forward-test vague/new-project intake, existing dirty projects, interrupted
   sessions, missing tools, declined external skills, release/prerelease/no-release
   selection and existing installations in isolated projects. Record real agent
   evidence separately from deterministic package tests.
5. Prepare one immutable candidate with package/registry/regression evidence,
   independent review, platform installation smokes and explicit remaining limits.
   Obtain owner approval before publication. Update public capability claims only
   to match the package actually released.

The current onboarding change implements presentation and manual version guidance.
It does not publish these missing helpers or establish automatic bootstrap behavior.
