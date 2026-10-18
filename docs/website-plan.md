# LittleDevTeam Website — approved plan, revision 1

User decision: “PLEASE IMPLEMENT THIS PLAN” in this chat on 2026-10-18,
followed by the complete LittleDevTeam Website – Nebula Design und Dokumentation
proposal. This document records that proposal for implementation and review.

## Goal and scope

A modern German/English website for beginners, Codex users and experienced teams.
Explain the skill, let visitors explore its workflow, and provide installation
instructions. Explicitly explain that this website is built with LittleDevTeam
as a demonstration; document actual decisions, commits and checks in a case study.
The first release includes an introduction and technical reference. No live agent
runs, accounts or backend.

## Visual design and content

Dark space/nebula background with dark blue, purple, magenta and red gradients;
rounded surfaces, fine borders, controlled blur and glow. Locally bundled Space
Grotesk headings and Inter body font with their licenses. Slow nebula movement and
gentle transitions, no 3D or scroll-driven camera. Disable decorative animation for
reduced-motion preferences. Documentation uses calm opaque surfaces and readable
code blocks. Dark-only first release. LittleDevTeam wordmark and SVG orbit mark.

- Home: value, installation/workflow actions, understandable process, technical
  benefits and explicit demonstration-project notice.
- Installation: prerequisites; project and personal setup; Windows/macOS/Linux;
  verification, update, removal and troubleshooting.
- Guide: first request, requirements, architecture, approval, verification, resume.
- Documentation: profiles, approvals, memory, states/snapshots, validator commands,
  registry/external skills and limits.
- Interactive demo: predefined documentation-website request, discovery,
  architecture, approval/revision, implementation, verification, review, next
  iteration and reset. Explicit browser-only simulation.
- Built with LittleDevTeam: real website history and selected public evidence;
  never automatically import private local approval files or fabricate independence.

Header: wordmark, documentation, guide, demo, language, GitHub, highlighted install
action. Documentation has a sidebar, contents, search and copyable examples.

## Technology and interfaces

Astro, Starlight, TypeScript, Markdown/MDX, own CSS and small browser scripts.
Independent `website/` project, npm lockfile and Node.js 24. Preserve existing
Python tools. Static pages, assets and Pagefind index, no server APIs. Preserve
skill identifiers, commands and formats. German `/ltd-skill/de/…` and English
`/ltd-skill/en/…`, start address leads to German. Matching page keys and complete
translations; language switch keeps the corresponding page; localized search.
Installation copies the complete skill for project/personal use according to
official Codex skill docs. No new installer or imaginary `ldt` command. State
which Git revision documentation describes; distinguish drafts and unreleased work.

## Milestones and mandatory checks

Balanced profile and separate website state. Own feature branch/worktree from
published `main`, preserving concurrent skill development. Start with W1; present
the concrete result and evidence at each milestone before advancing.

| ID | Result | Required checks |
| --- | --- | --- |
| W1 | Design foundation, responsive home/navigation, both languages, full installation and first guide | production build; type check; internal links; browser checks in both languages and mobile navigation |
| W2 | Full reference, search, interactive demo and case study with available actual evidence | content/source comparison; translation completeness; search/interaction checks; installation smoke checks |
| W3 | Final review and tested GitHub Pages release | full website checks; existing skill checks; accessibility; performance; published URL checks |

## Release acceptance and defaults

Responsive checks at 375/768/1440 px, no horizontal overflow. Keyboard access and
visible focus for navigation, search, language, demo and copying. Playwright/axe
with no serious/critical accessibility findings. Correct localized search and empty
results. Temporary-directory installation/update/removal smoke checks on Windows,
macOS and Linux, separate from actual Codex discovery verification. All translations,
links, base paths and direct routes work in production. Mobile Lighthouse >=90 on
home and representative docs. Content readable without JavaScript. GitHub Actions
checks PRs. Deploy GitHub Pages only after approval of the concrete revision, at
https://youngjibbit95.github.io/ltd-skill/ initially without a custom domain. Retain
the previous deployment artifact for recovery.

German default, informal “du”, complete English. No analytics or remote fonts.
Project license requires an owner decision. W1 does not implement W2 or deploy W3.
