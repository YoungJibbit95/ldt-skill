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

## Regression completeness

Run the repository's own discovery command, never a curated list:

```sh
python -B -m unittest discover -s tests
```

A curated list can omit the M1a differential oracle
(`tests/test_core_equivalence.py`) and hide a real failure. The oracle must stay
byte-identical; only the documented CLI extension is tolerated, and the
comparison normalises nothing else.

## Independent review

A material change gets an independent review by a separate agent with its own
session. The reviewer reproduces the claims, not just the structure. Before
recording a completion:

1. the full suite is green under the discovery command,
2. the independent review ran and its material findings are repaired,
3. the repairs are re-verified, and the regression covers the repaired
   behaviour, not only the internal flag,
4. the snapshot that is approved is the one the review actually saw.

Do not rewrite an earlier approval record. When a snapshot moves, record a new
decision for the new revision and keep the earlier one as history.

## Native agent execution

Agent work runs through the harness runtime, not through Python stubs. Record
the session id, the agent, the model and the provider fallbacks. A review
counts only when its report is bound to the revision it reviewed and the
reviewer session is verifiable. A fixture run is never an independent review.
