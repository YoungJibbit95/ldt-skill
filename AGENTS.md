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

The original Nebula plan is preserved in `docs/website-plan.md`. W1 and the exact W2 result (`db71e831f3345767282bf12ffd47c9898ab6aca9`) were accepted. The user explicitly approved W3 Revision 1 in `docs/website-w3-proposal.md`, SHA-256 `8a499db3f1ccc24b4f18a453708333d8b614f1b2583a7d663864a5a427e0df9f`, for bounded refinement, release preparation and verification. Use the verified installed writing skill for human-facing changes. Merge, Pages/environment settings and deployment require separate concrete authorization. Public URL and public performance checks remain incomplete until authorized publication; do not report W3 as fully complete beforehand. Keep website work in its own worktree/branch and preserve the skill's existing development milestones.

## Verification and publication

- Runtime helpers require Python 3.10+ and use the standard library. Run package/registry checks and the existing regression suite when relevant; commands are in `README.md`.
- Report skipped or unavailable checks accurately. A self-review is not an independent review.
- Keep local approval records, evaluation logs, secrets and generated output out of Git. Do not add a project license without an owner decision.
- Use scoped branches and reviewable changes after initial bootstrap. Merge and deployment require authorization for the concrete result.
