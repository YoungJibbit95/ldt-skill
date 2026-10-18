# LittleDevTeam website

The approved [website plan](../docs/website-plan.md) provides a bilingual Nebula home,
installation and first-task guide, full reference, localized search, interactive
simulation, and evidence-based case study. W3 adds design/content refinement,
release preparation and verification. See the exact
[W3 proposal](../docs/website-w3-proposal.md) and
[release procedure](../docs/website-release.md). Publication needs separate approval.

Use Node.js 24 (`.nvmrc`) and npm:

```sh
npm ci
npm run dev
npm run check
npm run check:content
npm run build
npm run check:links
npm run test:release
npx playwright install chromium
npm test
npm run test:install
```

Development and preview serve `/ltd-skill/de/` and `/ltd-skill/en/`. The deployment
base is always `/ltd-skill/`; test the built site, not just development mode.
`npm run preview -- --port 4321` serves the production build used by Playwright.

Content documents skill revision `9a062eb9de0990ce1074dd677d26e5a528ee14a0`.
Do not import local approvals/evaluation logs or claim checks not actually run.
The original worktree's ongoing skill development is outside website work.

`check:content` needs Python 3.10+ and Git. It checks the source pin, matching DE/EN
documentation, the actual CLI command table, and executable package/registry/state
examples. `test:install` runs the tutorial in temporary projects and substituted
personal-home paths, tests no-overwrite, synthetic staged replacement, removal and
recovery, and never changes active installations. CI runs these smokes on Windows,
macOS and Linux. These checks do not establish actual Codex discovery.

Fonts are bundled locally. Public license texts are copied unchanged from the
installed font packages and must remain alongside distributed font assets. See
[third-party notices](THIRD_PARTY_NOTICES.md). These licenses do not license this project.

The `postcss-selector-parser` override uses the patched 7.x parser in the build-time
Expressive Code dependency chain. The generated code-block CSS is verified by the
production build and browser checks; do not apply a forced Starlight downgrade.

GitHub Actions checks pull requests and creates inert candidates after successful
internal push/manual validation runs. The Pages workflow runs only on manual
dispatch after exact merge/setup/deployment approvals; it never enables Pages.

`npm run test:release` runs built-in Node tests against the Python archive verifier,
including tampered manifests/archives, wrong provenance and unsafe members.
The archive verifier writes files only after validating the entire inventory.

With the production preview running, measure the full local series:

```sh
npm run measure -- --sha FULL_SOURCE_SHA --output reports/local-series-1
```

Lighthouse is pinned to 13.5.0. It uses Playwright's Chromium, fresh profiles and
three serial mobile runs per DE/EN home/installation URL; each median must reach
90. Keep every report. Actual results belong in the revision's completion report.
Do not overwrite prior series or label local measurements as public evidence.
The release procedure documents the opt-in public checker and separate public
performance series. Neither tool deploys the website.
