# LittleDevTeam website

W1 of the approved [website plan](../docs/website-plan.md): bilingual Nebula home,
introduction, full installation guide and first-task walkthrough. The interactive
demo, full reference and detailed case study are W2; publication is W3.

Use Node.js 24 (`.nvmrc`) and npm:

```sh
npm ci
npm run dev
npm run check
npm run build
npm run check:links
npx playwright install chromium
npm test
```

Development and preview serve `/ltd-skill/de/` and `/ltd-skill/en/`. The deployment
base is always `/ltd-skill/`; test the built site, not just development mode.
`npm run preview -- --port 4321` serves the production build used by Playwright.

Content documents skill revision `9a062eb9de0990ce1074dd677d26e5a528ee14a0`.
Do not import local approvals/evaluation logs or claim checks not actually run.
The original worktree's ongoing skill development is outside W1.

Fonts are bundled locally. Public license texts are copied unchanged from the
installed font packages and must remain alongside distributed font assets. See
[third-party notices](THIRD_PARTY_NOTICES.md). These licenses do not license this project.

The `postcss-selector-parser` override uses the patched 7.x parser in the build-time
Expressive Code dependency chain. The generated code-block CSS is verified by the
production build and browser checks; do not apply a forced Starlight downgrade.

GitHub Actions checks the website on pull requests. W1 does not configure deployment.
