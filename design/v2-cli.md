# Little Dev Team CLI — proposed technical design

Status: optional V2 component, unimplemented and pending approval. Executable name
`ldt` is provisional; packaging/name availability must be checked before release.
See [runtime/library research](research/runtime-cli.md) for observed versions and
official sources. No dependency was installed and no service was started.

## Stack and boundaries

Propose Python >=3.10, standard-library command parsing, and an optional
prompt_toolkit terminal view. This reuses V1's Python core without a Node/Rust
bridge. Keep commands functional without the optional extra. The researched
prompt_toolkit release is 3.0.53; final artifact hashes/licenses/dependency pins
must be reviewed in the implementation milestone, not silently installed now.

Questionary adds convenience but needs Escape integration; InquirerPy's older
release needs maintenance review; Textual introduces a larger framework and
dependency surface than the initial menus require. Use established widgets/key
bindings, not a custom terminal framework. No auto-update or on-demand dependency install.

Layers: rendering → application commands → one shared deterministic core →
permission-checked filesystem/runtime adapters. Rendering never writes approval
state directly. Query commands are read-only; mutations preview, bind and persist
an exact action. The wheel includes the same core source as the standalone skill;
parity/version compatibility is tested before packaging.

## Commands and navigation

Proposed commands, not existing implementations:

```text
ldt project new|open|status
ldt plan feature
ldt milestone continue
ldt approvals list|inspect|decide
ldt team inspect
ldt checks run
ldt skills list|discover|recommend|inspect|verify
ldt skills install|enable|disable|audit|update
ldt settings
```

Plain invocation shows Project, Plan/Continue, Approvals, Skills, Team/Checks,
Settings and Exit; deeper operations are contextual. Don't require 12 top-level
steps. Derive stack/existing repo facts; ask only missing, high-value decisions.
Project initialization collects objective, profile, domain-sensitive constraints,
required human checkpoints and external-skill preferences progressively. There
is no setting that turns broad approval into unrelated merge/deploy authority.

Interactive keys: Up/Down move, Enter selects, Space toggles multi-selection,
Escape/Back returns without committing, Cancel abandons the draft, Ctrl-C exits
cleanly. The focused item is never automatically approved. Approval panels show
project, action kind, exact scope/revision, diff/policy delta, risks and evidence.
Destructive/external actions need their own explicit decision and preview.

Non-TTY operation accepts explicit subcommands and offers stable JSON/no-color
output. Missing required decisions produce an actionable pending state, not a
hang, default yes, or success code. A broad `--yes` option is prohibited. Exact
automation receipts, if later supported, need a separately approved authority
model; local JSON alone isn't proof of a human decision.

English and German messages share stable internal IDs/hashes; only presentation
is localized. Language changes don't invalidate approval. No unnecessary internal
department jargon. Keyboard behavior is necessary but not sufficient for screen
reader accessibility; provide plain prompts and test supported environments.

## Skill Manager interaction

Choose project → inspect capability needs → view relevant shortlist → inspect
source/license/runtime/effects → select → preview exact file/dependency changes →
request install decision → supported install/verification → request task activation
decision. Back/cancel makes no changes. Selection, installation, activation,
delegation and tool execution are distinct operations, even in a combined UI.
Installation stages inert files outside host discovery roots. `enable` requires
verified host isolation/discovery controls or uses explicit approved instructions
in an isolated worker; unsupported exposure fails closed. `disable` stops future
dispatch and reports contexts requiring termination/replacement, never claims to
erase loaded instructions. Display pre-existing host exposure separately.

`verify` reports source/security/test evidence separately and performs no arbitrary
code execution. Compatibility smoke tests require an explicit test-execution
grant. `audit` is read-only metadata comparison unless an authorized specialist
assessment is chosen. `update` shows revision/content/permission deltas; it never
preserves consent for silently expanded privileges. Preview and bind the resolved
execution-manifest digest, not only the skill commit; mutable dependency downloads
block execution, and artifact/runtime configuration changes require renewed evidence.

## Runtime adapters and authentication

| Adapter | Proposed scope | Verification boundary |
| --- | --- | --- |
| Manual/native session (first) | Produce compact exact-context handoff; user opens Codex with the skill | No LDT-launched service or claimed programmatic agent control; reconcile returned evidence before advancing |
| Bounded CLI exec (later opt-in) | One approved task through installed `codex exec`, JSON events if supported | Probe version/help/capabilities, explicit cwd/sandbox/task, timeout/cancel; process is a session/job, not a native subagent |
| App-server/SDK pilot (deferred) | Rich session/events/runtime permission UI through supported protocol | Standalone app-server has the experimental/production caveat; official Python SDK is described as stable. Neither proposed LDT adapter is tested; require versioned compatibility tests and explicit pilot approval |

The installed CLI version observed was `0.163.0-alpha.10.2`; its help was exercised,
not a real execution adapter. Don't assume this session's subagent API is an
external CLI API. The adapter exposes capability flags (sessions, events, review,
native delegation, permission requests, token metrics); unsupported flags stay
false and route to manual/sequential operation. No invented `spawn_agent` RPC.

For a future app-server adapter, use documented initialization and thread/turn
operations only after version/schema negotiation. Never use removed Codex MCP
server launch examples. Runtime command/file permissions are separate from
architecture/iteration/install decisions and cannot be satisfied by one generic yes.
Do not enable automatic timeout acceptance for LDT decisions.

Codex owns sign-in. No copying tokens into state, environment dumps or logs, no
automatic account creation/login, and no API key provisioning in the CLI design.
If authentication/model access is missing, explain and stop dependent execution.
SDK installation/authentication work needs separate permission. A locally working
CLI doesn't prove an SDK or app-server adapter has production support.

## Persistence and cancellation

Use one project writer, a short-lived lock and compare-and-swap revision checks.
Save atomically through a same-directory temporary file after validation; retain
previous valid state/evidence. Revalidate action subject immediately before
dispatch and after relevant results. Don't claim whole-repository atomicity.
Unexpected changes or cancellation never advance the milestone.

Callbacks/events carry task and action IDs. Resume reconciles actual child/session
status, source/policy hashes and granted effects; don't restart a lost process
blindly. Ctrl-C cancels/interrupts only the owned job where supported, waits for
confirmation, records uncertain completion, and leaves pending approvals pending.
No global process-killing, implicit rollback of user edits, or orphaned service
claims. Automatic retries must be bounded and idempotent for that specific action.

Treat filenames, repo metadata, skill text and logs as untrusted terminal content:
escape control sequences, sanitize links, bound output, and never interpolate
data into shell strings. Invoke tools with argv and explicit cwd. Installation
destinations and rollback targets must resolve inside the approved root; refuse
symlink traversal, path collisions and unknown existing files.

## Acceptance and open questions

Test the same command payload against conversational/core/plain/JSON/TUI paths;
all must reach identical policy decisions. Include keyboard navigation and Escape,
stale scope, missing consent, interrupted writes, competing writers, changed source,
installer rollback, dependency artifact drift, pre-consent host discovery,
revocation in loaded contexts, unknown schemas, unavailable Codex and disconnected terminals.
Use prompt_toolkit's controlled input/output fixtures plus real Windows/macOS/Linux
smoke runs; no screen-reader claim from mocked keyboard tests alone.

Open decisions: final package/distribution name, supported terminal/OS matrix,
dependency pin audit, SDK/app-server production suitability, organizational receipt
authority, runtime event persistence and model/token telemetry. Initial manual
integration keeps these uncertainties from blocking native skill use.
