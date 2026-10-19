# Website release procedure

This procedure prepares and promotes the static LittleDevTeam website. It does
not install the skill or change the documented skill revision. The website still
documents skill `9a062eb9de0990ce1074dd677d26e5a528ee14a0`; each website release has
its own source SHA in `/ldt-skill/release.json`.

W3 implementation approval permits release preparation and tests. It does not
permit merging, configuring Pages or environments, dispatching publication, or
declaring the website publicly verified. Record those decisions separately.

## Prepare an exact candidate

Use Node 24 and Python 3.10 or later. Work from the repository root unless a step
says otherwise. Preserve the lockfile and use `npm ci` in `website/`.

```sh
cd website
npm ci
npm run check:content
npm run check
npm run test:release
npm run build
npm run check:links
npx playwright install chromium
npm test
npm run test:install
```

The existing skill CI remains unchanged. `Validate website` also runs the same
Linux/Windows and Python 3.10/3.12 matrix so a branch candidate has skill evidence
at its exact source SHA. Installation smoke tests run on Linux, Windows and macOS.
They validate file operations and Python helpers; they do not prove Codex discovery.

The website job runs Lighthouse 13.5.0 with the installed Playwright Chromium.
It measures the German and English home and installation pages: three serial
mobile runs per URL, each with a fresh browser profile and storage reset. Each
URL must have a median performance score of at least 90. The job retains all
twelve HTML and JSON reports, configuration, browser/tool versions and runner
metadata. It does not select successful retries or replace failed runs.

To run the identical local series, start `npm run preview -- --port 4321` in one
terminal. In a second terminal in `website/`, run:

```sh
npm run measure -- --sha FULL_SOURCE_SHA --output reports/local-series-1
```

Use a new output directory for each complete series and retain failed series.
Measure the final committed source without concurrent builds or browser tests.
Local results establish only the local performance subcheck. The mandatory
`performance` check remains `not_run` until the separate public series passes.

On a successful internal push or manual validation run, the candidate job waits
for the website, installation and skill jobs. It then packages the checked build
without rebuilding. Pull-request runs produce reports but no deployable candidate;
fork and PR origins are rejected by publication validation.

Download the successful run's `website-candidate` artifact and
`website-validated-build` reports. The candidate zip contains exactly:

- `site.tar.gz`: built files plus public `release.json` identity.
- `manifest.json`: repository, fixed workflow path, run ID/attempt, source SHA,
  tool versions, same-run evidence, individual file hashes and archive SHA-256.

The manifest sits outside the archive, avoiding a self-referencing checksum.
Private approvals, local development logs and review records are not imported.
Candidate metadata says public checks are `not_run`; a green build does not
authenticate human approval or an independent review.

## Review the release record

The completion report must name the full source SHA, review-bound snapshot,
PR, successful candidate run ID, artifact ID, archive SHA-256, optional manifest
SHA-256, artifact expiry and a successful download receipt. Include the actual
local Lighthouse scores and every failed, skipped or unavailable check. Bind
independent design, content, engineering and quality review evidence to that
same source revision. A later source change invalidates that binding.

GitHub artifacts and reports request 90-day retention; repository policy may
shorten it. Inspect the actual API `expires_at` value and secure the candidate
and reports before they expire. Expired artifacts cannot be promoted by this
workflow. A replacement candidate requires its own exact evidence and approval.

These read-only commands inspect a candidate. Replace uppercase operands with
the reviewed values; do not type the placeholders literally.

```sh
gh run view CANDIDATE_RUN --repo YoungJibbit95/ldt-skill
gh api repos/YoungJibbit95/ldt-skill/actions/artifacts/ARTIFACT_ID
gh run download CANDIDATE_RUN --repo YoungJibbit95/ldt-skill --name website-candidate --dir .architect-dev-team/website/downloaded-candidate
```

On PowerShell, calculate hashes with
`Get-FileHash -Algorithm SHA256 -LiteralPath PATH`. On macOS use
`shasum -a 256 PATH`; on Linux use `sha256sum PATH`.

Before publication, obtain three explicit decisions for the concrete result:
merge the named revision, configure Pages/environment if needed, and deploy
the named candidate artifact. These decisions may be given together, but each
must be clear. No workflow performs repository or environment setup. Configure
Pages to use GitHub Actions only after that setup is authorized; configure
`github-pages` protection/review rules as agreed by the owner.

The source SHA must be reachable from `main` before dispatch. Squash/rebase
creates a new SHA: rerun validation for the new identity and obtain the matching
release approval. Never substitute an older candidate because its tree looks
equivalent. A normal merge that retains the approved source commit can preserve
its identity, subject to the exact approval.

## Manual publication after separate authorization

`Publish approved website artifact` has only `workflow_dispatch`. Pushes, merges
and green tests do not deploy. Dispatch it only after the three decisions above.

The following command publishes. It is an operator instruction, not a step
authorized by W3 implementation approval:

```sh
gh workflow run pages.yml --repo YoungJibbit95/ldt-skill --ref main \
  -f approved_sha=FULL_SOURCE_SHA \
  -f candidate_run=CANDIDATE_RUN \
  -f artifact_id=ARTIFACT_ID \
  -f archive_hash=ARCHIVE_SHA256 \
  -f manifest_hash=MANIFEST_SHA256
```

Omit `manifest_hash` only if the approval record omits it. Supplying it adds an
exact outer-manifest binding; the archive hash is always required. In PowerShell,
put the command on one line or use PowerShell's continuation syntax.

The validation job has read-only repository/actions permissions. Its tools come
from trusted `main`, not from the downloaded archive. It obtains run and artifact
metadata directly from GitHub and rejects wrong repository, fork, workflow,
event, revision, run identity, conclusion or expired artifact. It checks that the
source is reachable from `main`, then checks the approved archive hash, optional
manifest hash, every member's hash and public identity. It rejects absolute paths,
traversal, duplicate members, links and oversized archives before extraction.
Nothing from the archive is executed.

The separate deployment job needs successful validation and uses only
`pages: write`, `id-token: write` and the `github-pages` environment. It promotes
the verified file bytes through the official Pages artifact wrapper; it does
not rebuild the website. The workflow never enables Pages or changes settings.
Deployment success alone does not complete W3.

## Verify the public release

After deployment, the read-only evidence job checks
`https://youngjibbit95.github.io/ldt-skill/`. Release identity propagation may retry
for at most five minutes; attempts are logged. Other failures remain failures.
The job checks all direct DE/EN routes and reloads, release identity, German entry,
canonical/hreflang, language switching, asset/font loading, Pagefind search and
empty state, keyboard focus, demo, mobile menu/copy, representative live Axe and
No-JavaScript behavior, and a real HTTP 404 for an unknown URL.

The job then runs the separate twelve-run public Lighthouse series with the same
policy. It preserves successful and failed public evidence for the requested
90 days. To repeat a complete read-only public verification with a new report
directory, use:

```sh
cd website
npm run check:published -- --public --sha FULL_SOURCE_SHA --output reports/public-urls-1
npm run measure -- --public --origin https://youngjibbit95.github.io --sha FULL_SOURCE_SHA --output reports/public-performance-1
```

These tools refuse other origins. They never publish or change GitHub settings.
Retain complete repeats and explain why they were needed. Keep `published URL
checks` and `performance` open until actual public evidence passes. Bind the final
review snapshot and completion report to the deployed revision before asking for
W3 completion approval. Do not advance automatically to W4.

## Recovery

There is no previous deployed website before the first release. The first
candidate can be deployed again after a concrete redeployment approval; it
cannot restore a nonexistent older site. Disabling Pages needs separate owner
authorization. A failed public check must be reported even if deployment passed.

After a publicly verified first release, preserve that candidate, manifest,
GitHub provenance receipt and public reports as the first recovery baseline.
Before each later release, download the previous verified artifacts and check
their hashes and expiry. Do not promise recovery from artifacts already expired.

To restore an available earlier baseline, obtain approval for its exact SHA,
candidate run, artifact ID and hashes, then use the same manual workflow. It
revalidates the original successful provenance, deploys those bytes and repeats
all public checks and measurements. If the original GitHub artifact has expired,
this workflow refuses it; arrange a separately reviewed recovery process rather
than bypassing provenance checks or uploading an unverified substitute.
