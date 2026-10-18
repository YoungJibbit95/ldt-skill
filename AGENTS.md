# LittleDevTeam repository

## Product and source of truth

- LittleDevTeam is the project name; `architect-dev-team` is the existing skill identifier. Preserve that identifier unless a migration is explicitly scoped.
- Read `.agents/skills/architect-dev-team/SKILL.md` when using the LittleDevTeam workflow and load only relevant references.
- Inspect Git status before edits. Existing source, tests and local milestone records may contain work from another ongoing task; preserve it.
- Files under `design/` are proposals and historical research, not evidence of shipped functionality. Confirm behavior against current source and actual checks.
- Local `.architect-dev-team/` records belong to their existing scopes. Do not overwrite the skill-development state to start website work; use a separate website state directory.

## Website and GitHub work

The website/GitHub agent owns repository setup and the future website project. The user requested a modern website with documentation, a practical guide and an installation tutorial. See `docs/website-brief.md` for the agreed brief.

The website must explicitly explain that it was developed with the LittleDevTeam skill as a demonstration. Record real planning, human decisions, implementation and verification. Do not fabricate independent reviews, test results, performance benefits or feature availability.

Repository bootstrap is authorized separately from website implementation. The next website step is planning with the user; do not infer a website architecture approval from the bootstrap request. Preserve the skill's existing development milestones rather than advancing them through website work.

## Verification and publication

- Runtime helpers require Python 3.10+ and use the standard library. Run package/registry checks and the existing regression suite when relevant; commands are in `README.md`.
- Report skipped or unavailable checks accurately. A self-review is not an independent review.
- Keep local approval records, evaluation logs, secrets and generated output out of Git. Do not add a project license without an owner decision.
- Use scoped branches and reviewable changes after initial bootstrap. Merge and deployment require authorization for the concrete result.
