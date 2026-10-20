# Native Runtime Adapter

`ldt_core.runtime` is the single place that talks to the OpenCode CLI. It owns
process invocation, model selection, session evidence and independence checks.

Everything here is a documented OpenCode CLI call. No invented API, no
background service, no second execution system.

## Detection

```python
from ldt_core.runtime import detect_runtime
info = detect_runtime(refresh=True)
info.available      # bool
info.executable     # path to the CLI
info.version        # e.g. "opencode v2.0.32"
info.agents         # native agent ids
info.models         # model ids the runtime reports
```

The CLI is located on `PATH` first, then in the known npm and desktop install
locations. When nothing is found the adapter reports `available: False` with a
reason. It never pretends to be available.

## Role mapping

| LDT role | Native agent | Write access |
|----------|--------------|--------------|
| research | `explore` | none |
| architect | `plan` | none for edits |
| implementer | `general` | native set |
| critic | `explore` | none |
| integration | `general` | native set |

`is_read_only_agent(agent)` reports whether the native agent can write files.
The answer is derived from the runtime's own permission data
(`opencode debug agents`): an agent counts as read-only when its permission
set denies the write actions. It is a runtime property, not a policy claim.

When the runtime cannot be queried, no agent is treated as read-only. An
unverified agent must not be used to grant a write boundary, and a review
that depends on one is reported as unavailable.

## Dispatch

```python
run = dispatch(prompt, role="critic", cwd=root, model_profile="high")
run.status          # completed | failed | unavailable
run.session_id      # session id reported by the runtime
run.agent           # native agent that ran
run.model           # model that ran
run.output          # agent text output
run.evidence        # execution_mode, fallbacks, returncode, executable
```

A fresh session is created per dispatch unless an explicit `session_id` is
given. Implementation and criticism therefore never share a session.

### The prompt has a limit

The prompt travels as a command line argument, and an argument has a length
limit. A prompt that is too long is cut before the run, and the cut is
stated in the prompt itself, so the agent knows that it is not seeing
everything. The prompts therefore carry the result of the previous step,
never the raw answer of an agent.

## Model selection

```python
model_candidates("high", available_models)
# -> ordered chain, intersected with the models the runtime reports
```

Order expresses capability preference, not price. Listing a model does not
prove it is usable, so `dispatch` walks the chain and continues to the next
entry on a provider error. Every attempt is recorded in
`evidence["model_fallbacks"]`. The runtime's own default model is the last
resort.

The chain is never padded with invented identifiers. If the runtime reports no
usable model, the run fails honestly instead of guessing.

## Session evidence

```python
verify_session(session_id, cwd)
# -> {"verified": bool, "agent": ..., "outcome": ..., "tokens": ..., "time": ...}
```

Uses `opencode session export <id>`. A session that cannot be exported is not
verified.

## Independence

```python
independence_report(implementer_run, critic_run, cwd)
# -> {"independence": "independent" | "unavailable", "reasons": [...], ...}
```

Independence requires all of:
1. both runs reached the real runtime,
2. distinct session ids,
3. both sessions independently verifiable,
4. the critic ran under a read-only native agent.

A missing or duplicated artifact fails. Self-declared metadata never passes.

## Agent permissions

```python
details = agent_permissions()      # id -> {mode, permissions}
read_only = read_only_agents()    # ids that cannot write
```

`runtime detect` reports the read-only agents it found. An empty list means
the runtime could not be queried, not that every agent is writable.

## Test fixture mode

`LDT_RUNTIME_FIXTURE=<file.json>` replaces the CLI call with canned outputs.
The fixture is used so deterministic tests need no model calls. It is never
silent: every run made this way carries
`evidence["execution_mode"] == "fixture"`, and both `independence_report` and
the integration gate refuse fixture runs. A fixture can never be reported as
native agent execution.
