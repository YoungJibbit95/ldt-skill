# Read-only project inventory

`ldt_core.inventory(root)` returns a bounded, JSON-compatible inventory. It reads
project facts without executing configuration, scripts, Git, external tools or
network calls. It does not recommend skills, install anything or grant consent.
Use it during discovery only when the observed stack would help the task.

The API is exported by the existing shared core. There is no new CLI command.
From Python, put the skill's `scripts` directory on the import path, then call:

```python
import json
from ldt_core import inventory

result = inventory(project_directory)
print(json.dumps(result, sort_keys=True, ensure_ascii=True))
```

Use an explicit local project root and a stable working tree. The API reads only;
the caller decides whether and where to save its output. Invalid or inaccessible
roots raise the shared `Invalid` exception, without echoing the absolute path.

## Output and evidence

`output_version: 1` versions this inventory output, independently of registry,
snapshot and project-state schemas. Those existing schemas are unchanged.

- `observations` report file/directory presence, a parsed JSON object, or known
  dependency keys. Each has `kind`, `value`, and relative `evidence.path`/`signal`.
- `inferences` report likely languages, frameworks, platforms and tooling. A
  filename or declared dependency is evidence of a signal, not runtime behavior.
- `capability_needs` group generic engineering/assessment needs with evidence
  paths and `status: inferred`. They contain no skill choice, ranking or action.
- `unknowns` distinguish unresolved runtime, compatibility, format and consent
  questions from confirmed observations.
- `coverage` always says `complete: false`: this is an allowlisted discovery aid,
  not an exhaustive source inventory. It records limits, exclusions, explicit
  issues and counts. A result with no issues is still bounded and incomplete.

A `.git` file/directory is only a marker observation. Its contents, hooks and
configuration are not read; Git is not invoked. A linked marker is skipped. A
non-Git directory works equally well. Marker absence does not establish that a
directory has no parent Git context.

`.agents/skills/<lowercase-hyphenated-id>/SKILL.md` is observed by file presence,
without reading its instructions. Presence establishes neither provenance, trust,
compatibility, activation nor user permission. Other install locations are not
searched. No external skill is executed by inventory.

## Supported scope

The root and allowlisted structure directories are inspected: `src`, `app`,
`apps`, `packages`, `lib`, `tests`, `test`, `backend`, `frontend`, `server`,
`client`, `services`, `web`, `docs`, plus `.github/workflows` and `.agents/skills`.
Immediate named workspaces under `apps`, `packages` and `services` are supported.
Arbitrary directories and dependency/generated trees are excluded.

Only `package.json` contents are interpreted: strict UTF-8 JSON with duplicate
keys/non-finite numbers rejected. Dependency sections must be objects with string
values. Only a fixed catalog of technology dependency names is emitted. Private
package names, versions, scripts, URLs, arbitrary keys and values are not returned.
Do not use inventory as a sanitizer: a selected manifest can contain sensitive
bytes, which are briefly read into memory even though arbitrary contents are
never emitted or logged.

Other supported names are presence-only signals: Python, Rust, Go, JVM, Ruby,
PHP, Dart, Swift and CMake manifests; common TypeScript, Next, Vite, test and
deployment configs. TOML/YAML/executable configuration validity is **unknown**.
Selected source extensions provide language inferences without opening source
files. The implementation constants specify the exact bounded catalog. Unsupported
languages, manifests and formats remain unknown rather than guessed.

## Safety and limits

Current limits: depth 5, 128 directory attempts, 256 entries per directory, 4096 total
entries, 128 KiB per selected manifest and 2 MiB total manifest bytes. Overflow
discards that directory's unordered entry set; no arbitrary partial entry order
becomes a finding. Results use stable sorting and have no timestamp or absolute
root. Missing, malformed, unreadable or changing inputs become coverage issues.
The per-directory check may consume one overflow sentinel within the total entry
budget. Reaching the total budget stops before another directory open or iterator
read, conservatively leaving coverage incomplete even at an exact boundary.
Directory attempts consume budget even when reading fails; `directories_scanned`
counts only successful scans. Unreadable inputs cannot bypass the attempt limit.

Evidence paths deliberately remain resolvable relative paths. They can reveal
workspace, source-file and installed-skill identifiers, including private names.
The privacy exclusion concerns arbitrary manifest name/value fields and unrelated
contents; it does not anonymize the required project evidence. Review these paths
before sharing an inventory outside its project context.

Paths are derived from enumerated safe relative names; arbitrary caller-selected
child paths are not accepted. Unsafe or sensitive names are excluded without
echoing them. Links, Windows reparse points, special files and manifest hard links
are skipped. Parent/file identity guards and no-follow/nonblocking file flags
where available reduce unsafe reads. A stable local tree remains required:
cross-platform traversal is not atomic against an actively racing writer, and
metadata checks cannot authenticate filesystem contents. Do not use it to attest
an attacker-controlled live filesystem. No credential store, `.env`, Git metadata
content or arbitrary home directory traversal is part of discovery.

Tests and evaluation evidence distinguish real native link checks from mocks and
platform skips. No discovery output changes approval records or gate semantics.
