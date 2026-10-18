# Read-only registry formats and migration

Registry validation checks metadata consistency, not source authenticity, safety,
license interpretation, compatibility, user consent or permission to execute.
All three supplied Schema 2 records remain untrusted `candidate` entries. No skill
code is bundled, installed or activated. This milestone provides no recommendation
engine, installer, runtime adapter or separate CLI application.

## Entry points

```text
python <validator> registry <registry/skills.json>
python <validator> registry <registry/index.json>
python <validator> registry <legacy-json> --migration-proposal
```

The existing helper prints `OK registry` on valid metadata. The explicit migration
flag prints a JSON proposal only. No command writes files, invokes candidate code,
follows remote URLs or installs dependencies. Filesystem errors stop the command.
Programmatic `registry_file(path)` may raise `Invalid` or ordinary I/O exceptions;
the facade reports those as `INVALID` with exit 1. Direct core exports are
`registry(value, root=None)`, `registry_record(value)`, `registry_file(path)` and
`migrate_registry(value)`. Importing them does not change streams or directories.

## Schema 1 compatibility

`registry/skills.json` and its original entry remain byte-identical. Original field,
trust and evidence prerequisites are retained. The helper's existing Schema 1
behavior is preserved; the new flag is an explicit opt-in. Schema 1 rules are not
silently strengthened by Schema 2. In particular, legacy URL parsing has its prior
limitations; malformed parser-level URLs may raise `ValueError` through the old
API. Schema 2 and the new migration path normalize those errors to `Invalid`.

## Schema 2 contract

`index.json` has exactly `schema_version: 2` and `records`, a list of `{id, path}`.
Paths must be `skills/<id>.json` beneath the explicit registry root. Index references
are regular files with no symlink traversal. Duplicate paths, IDs, primary names,
aliases or upstream repository/directory identities fail. Different revisions do
not create independent identities. The index has at most 256 references; each JSON
file is at most 1 MiB and aggregate ASCII-serialized record data at most 16 MiB.

Each record has exactly:

- `schema_version: 2` and `metadata`: the complete existing Schema 1 entry shape,
  including its original trust classification and evidence.
- `aliases`: distinct lowercase hyphenated identifiers. Alias evidence must match
  every alias once and bind the same pinned source. Names and IDs may coincide for
  their own record, but may not collide with another record or their own aliases.
- `verification`: `status`, `manifest_url`, `manifest_sha256`, `license_status`,
  `license_sha256`, `checked_at`, `alias_evidence`, `unknowns`.
- `runtime`: `requirements`, `effects`, `unknowns` string lists. Unknown effects or
  prerequisites must be explicitly stated rather than represented as known-empty.
- `lifecycle`: `status`, `reference`, `reason`. Status is `unknown`, `observed`,
  `catalog-deprecated` or `unavailable`; an unknown observation has no evidence URL.

M1b supports canonical GitHub repository URLs, full 40-character lowercase commits,
safe directory paths and pinned `blob`/`tree` evidence references. URL paths must
use ASCII graphic characters, without raw whitespace, controls, percent encoding,
query strings or fragments. Unsupported sources/encodings require a future reviewed
extension; they are not normalized silently. Record assertion strings must be UTF-8.
License identifiers use a single SPDX-style token; this is not a full SPDX parser.

`verification.status` is `unverified` or `source-verified`. Source verification
requires a manifest hash/date and exact canonical manifest URL. All source-verified
metadata evidence binds the same repository and revision; arbitrary revision
substrings do not establish binding. Unverified observations use null hash/date
and explicit unknowns. Evidence references remain assertions; validation does not
fetch them or prove their contents. External/local report references need a future
binding mechanism before they can support verified Schema 2 claims.

License status is `verified`, `declared` or `unverified`. Verified status needs a
license-text reference/hash and known identifier; declared status cites its manifest
declaration with a null text hash. Declared/unverified status requires uncertainty.
Legacy `reviewed`/`tested`/`approved` prerequisites still apply; Schema 2 additionally
requires verified source/license, resolved runtime uncertainty and pinned evidence.
No status transition or consent is inferred from successful validation.

## Three supplied identities

- `openai-gh-fix-ci`: original metadata preserved; selected Apache-2.0 text verified.
  The catalog README is deprecated while the pinned skill remains present.
- `anthropic-frontend-design`: actual manifest name `frontend-design`; selected
  Apache-2.0 text verified. Individual authorship and Codex compatibility are uncertain.
- `vercel-react-best-practices`: actual manifest name; `react-best-practices` is the
  verified directory-label alias. MIT is declared in the manifest; full license text
  and copyright notice are unresolved. Preserve Vercel Engineering/@shuding credits.

## Explicit migration proposals

`migrate_registry` accepts validated Schema 1 data and returns `proposal_version`,
`source_sha256`, `source_encoding`, a deep-copied `source`, proposed `index` and
`records`, `validation_issues`, and `ready_for_validation`. Every metadata value,
trust classification, unknown and original evidence entry is preserved. Source
checksums use compact sorted UTF-8 JSON; escaped lone-surrogate legacy values use
the explicitly identified ASCII-JSON fallback. CLI output is ASCII-escaped JSON so
those assertions survive without replacement. They remain unsupported Schema 2
drafts, with validation issues, rather than being dropped or corrupted.

Migration does not fetch missing verification or invent aliases/maintenance. It
marks source/license/effects uncertainty explicitly. Higher legacy trust or unsafe
legacy IDs/references may therefore remain unresolved drafts. Their original values
are retained without upgrade or downgrade. `ready_for_validation` means the proposal
meets structural checks, not that it was applied, approved, installed or safe.
Review the proposal separately and preserve the original before any future write.
