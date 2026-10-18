# Architecture and feature design

Inspect the narrow affected area first: repository instructions, working-tree
status, entrypoints, manifests, adjacent tests, interfaces, and architecture notes.
Record reusable facts with paths; expand only for a dependency or uncertainty.
Don't run setup scripts or install dependencies during discovery.

For new software, establish users, core behavior, deployment constraints, data,
integrations, and the first usable slice. For existing software, trace affected
paths and preserve compatible interfaces/conventions. Fix architectural debt only
when it blocks the requested outcome.

Ask one to three high-value questions at a time using available tools or chat.
Prioritize conflicting requirements, irreversible decisions, acceptance, and
sensitive data. Continue independent discovery while waiting. A timeout is not an
answer. Offer reversible defaults as explicit assumptions; resolve consequential
uncertainty before implementation.

Capture functional acceptance and relevant security, performance, accessibility,
reliability, integration, and testing requirements. Quantify design-driving
requirements. Don't manufacture a checklist document for a two-line change.

## Design package

Use [the architecture template](../assets/architecture.template.md) selectively:

- Current/desired behavior, scope and exclusions.
- Affected components, ownership, interfaces, data/dependency flow.
- Chosen technology and consequential alternatives/tradeoffs.
- Relevant trust boundaries, auth, sensitive data, failure modes, recovery,
  compatibility, migration/rollback, performance and reliability constraints.
- Small milestones with observable acceptance and mandatory checks.
- Assumptions, risks, unresolved questions, exact approval requested.

A paragraph and criteria suffice for a small feature. Diagrams clarify actual
boundaries/flows; no drawing tool is required. ADRs are for significant lasting
decisions: context, decision, alternatives, consequences. Follow repository format.
Target under 200 lines for an ordinary proposal; link existing documentation.

## Milestones and expansion

Prefer a testable vertical slice. Specify scope, acceptance, dependencies,
interfaces, required checks, and recovery before seeking approval. Don't split
tightly coupled edits into artificial agent tasks.

Record stable required check names in `milestone.required_checks` before computing
scope. These are the approved mandatory policy, separate from observed results.
Removing, renaming, demoting, or adding a mandatory check changes the policy and
needs a new scope approval. Keep human-readable commands and acceptance linked to
these names; a short feature can still use a short proposal and one meaningful check.

For features, compare the focused design to approved architecture. Revise affected
boundaries rather than replacing the system design. An interface, data model,
trust boundary, deployment, or scope change beyond approval requires a new design
version and approval. Routine choices within scope need no extra ceremony.
