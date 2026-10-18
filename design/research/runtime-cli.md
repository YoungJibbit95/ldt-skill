# Runtime and terminal-library research

Accessed 2026-10-18. Research only; nothing installed or launched as a service.

## Observed local runtime

Read-only probes `codex --version`, `codex --help`, `codex exec --help`, and
`codex app-server --help` succeeded. Installed version: **0.163.0-alpha.10.2**.

- Interactive CLI accepts a prompt and `--cd`/`-C` project directory.
- `exec` advertises `--json`, `--sandbox`, `--ephemeral`, `--output-schema`, and
  explicit working directory. These are observed flags, not an exercised LDT adapter.
- `app-server` is labeled experimental locally; help advertises stdio and local
  transport choices plus schema-generation commands. No server was started and
  no schemas or bindings were generated.
- This Codex session exposes actual spawn/message/wait subagent tools. That is
  evidence about this session, not a promise that a separate CLI process exposes
  those tools to an external application.
- Authentication was not inspected, changed, or exercised. LDT must not read or
  copy Codex credential files. A future adapter should let the supported Codex
  client own sign-in and show an authentication-required state when necessary.

## Current official integration evidence

[App-server documentation](https://learn.chatgpt.com/docs/app-server) describes
JSON-RPC initialization, session/turn handling, event delivery, and runtime
permission requests. Those execution permissions are separate from LDT design,
milestone, installation, merge, and deployment decisions.

[SDK documentation](https://learn.chatgpt.com/docs/codex-sdk) describes TypeScript
and Python clients; it describes the Python SDK as stable and its package drives
a pinned local runtime. That differs from the standalone app-server production
caveat below. No SDK was
installed or tested. Treat compatibility as a future adapter acceptance check.

[MCP migration guidance](https://learn.chatgpt.com/docs/mcp-server) says the old
Codex-as-MCP-server integration was removed and warns about experimental app-server
production support. Local help agrees on the experimental label. Use manual/native
session integration as the reliable first boundary; evaluate richer adapters in
an explicitly approved pilot. Do not copy obsolete cookbook launch commands.

[Subagent guidance](https://learn.chatgpt.com/docs/agent-configuration/subagents)
distinguishes actual delegated work from ordinary sessions. A spawned operating-system
process is never sufficient evidence that native Codex subagents exist.

## Terminal dependencies compared

Release facts were read from the publisher's PyPI JSON metadata on the access
date; license files were fetched from the corresponding upstream version tags.
Release recency is one maintenance signal, not a security assessment.

| Candidate | Observed release / upload date | Python / runtime dependencies | License source | Fit |
| --- | --- | --- | --- | --- |
| prompt_toolkit | 3.0.53 / 2026-07-26 | >=3.10; `wcwidth>=0.1.4` | [pinned license](https://github.com/prompt-toolkit/python-prompt-toolkit/blob/3.0.53/LICENSE), BSD terms | Direct key bindings, radio/checkbox widgets, explicit I/O; strongest provisional fit for a small terminal view |
| Questionary | 2.1.1 / 2025-08-28 | >=3.9; prompt_toolkit | [pinned MIT license](https://github.com/tmbo/questionary/blob/2.1.1/LICENSE) | Convenient prompts; adds a wrapper and needs Escape/Back integration verified |
| InquirerPy | 0.3.4 / 2022-06-27 | >=3.7,<4; prompt_toolkit, pfzy | [pinned MIT license](https://github.com/kazhala/InquirerPy/blob/0.3.4/LICENSE) | Convenient selection/keybinding API; older release is a review concern, not proof of abandonment |
| Textual | 8.2.8 / 2026-06-30 | >=3.9,<4; Rich, Markdown plugins, Pygments, platformdirs and others | [pinned MIT license](https://github.com/Textualize/textual/blob/v8.2.8/LICENSE) | Suitable for larger applications; unnecessary framework/dependency surface for the first menu-based milestone |

Metadata endpoints: [prompt_toolkit](https://pypi.org/pypi/prompt_toolkit/json),
[Questionary](https://pypi.org/pypi/questionary/json),
[InquirerPy](https://pypi.org/pypi/InquirerPy/json),
[Textual](https://pypi.org/pypi/textual/json). These endpoints are mutable observations;
the versioned license links and recorded releases identify what was researched.

Provisional choice for the proposal: standard-library command parsing and a
small optional prompt_toolkit view. No extra prompt framework, database service,
web server, or SDK dependency is needed for the first local command interface.
Package/hash pinning and dependency-license review remain implementation work.

[Keybinding documentation](https://python-prompt-toolkit.readthedocs.io/en/stable/pages/advanced_topics/key_bindings.html)
and [test I/O documentation](https://python-prompt-toolkit.readthedocs.io/en/stable/pages/advanced_topics/unit_testing.html)
support an Escape/Back cancellation contract and synthetic keyboard tests. Actual
Windows/macOS/Linux and screen-reader behavior still needs testing. Plain text,
no-color, noninteractive JSON, and explicit cancel behavior must work without the
optional terminal dependency. No terminal UI was built or certified here.
