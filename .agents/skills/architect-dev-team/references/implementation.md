# Implementation Protocol: Pair Execution, Repair, Integration

## Native agent execution

Agent work runs through the **OpenCode runtime**, not through Python stubs.

| Role | Native OpenCode agent | Write access | Why |
|------|----------------------|--------------|-----|
| Research specialist | `explore` | none (read-only) | A research task produces specifications, never project edits. |
| Implementer | `general` | scoped by the native agent set | Implements inside the contract and writes its tests. |
| Independent critic | `explore` | none (read-only) | The critic cannot modify production files even if instructed to. |
| Architecture lead | `plan` | none for edits | Planning must not change the tree. |

The write boundary is enforced by the **native agent permission set**, not by a
policy sentence. A critic dispatched as `explore` cannot write `src/**` even if
the prompt asks it to.

### Dispatch mechanism

`opencode run --agent <agent> --model <provider/model> --format json [--title T] <prompt>`

The runtime adapter (`scripts/ldt_core/runtime.py`) records:
- the session id reported by the runtime,
- the agent and model that actually ran,
- provider errors and the model fallback chain,
- the CLI binary and its version.

### Model selection and fallback

Role profiles map to an ordered model chain that is intersected with the models
the runtime actually reports (`opencode models`). Listing a model does not prove
it is usable, so the adapter tries the chain in order and continues to the next
entry on a provider error (quota exhausted, rate limit, upstream overload).
Every attempt and its error is recorded as evidence.

If the whole chain fails, the runtime's own default model is tried last.

### Session evidence

`opencode session export <session-id>` returns the recorded agent, outcome,
token counts and timestamps. Every independence decision is based on that
export, not on a self-declared field.

```
python <validator> runtime detect
python <validator> runtime agents
python <validator> runtime models
python <validator> runtime verify --session-id <id> --root <root>
```

### Honest fallback

If the runtime is unreachable, the adapter returns `unavailable` with a reason.
No findings, no independence and no test result is fabricated. A waived or
unavailable review is reported as such, never as an independent review.

## Pair Execution: Implementer + Independent Critic

### Principles
- **Separate contexts**: Different sessions, different agents, no shared private reasoning.
- **Critic gets**: Requirements, specifications, artifacts under review, and the
  implementer's reported result. It does not get the implementer's reasoning.
- **Critic writes**: Nothing in production. Tests only under an approved
  isolated area.
- **Independence**: The `rigorous` profile requires `independence: "independent"`
  **and** a hash-bound runtime evidence artifact that proves two distinct,
  verifiable session ids and a read-only critic agent. A self-declared
  independence string is not sufficient. Without the evidence the gate
  refuses the review.

### Implementer Contract
- Works from the task contract with clear acceptance criteria.
- Runs deterministic checks (unit, contract, lint, type).
- Produces: changes, findings, evidence, check results.

### Critic Contract
- Receives the task contract, the architecture, the implementer's reported result.
- Must return a validated `CriticReport` (see
  [critic quality](critic-quality.md)). A report that fails the contract
  fails the pair; the reviewer cannot declare its own success.
- Researches consequential, version-dependent or security-relevant questions.
- Produces findings with file:line, reproduction, spec reference and severity.
- May add tests only under `tests/critic/` or another approved isolated area.

### Repair Loop
1. Critic reports findings → Implementer repairs the affected group.
2. Max **2 targeted repair rounds per finding group**.
3. After 2 rounds: the Lead evaluates root cause, progress and remaining budget.
4. Escalation triggers: scope change, missing decision, security risk, budget
   exhausted, repair exhausted.

### Escalation to Lead
- Material scope/architecture change
- Missing domain decision
- Additional cost/permissions
- Critical security/data loss risk
- Budget exhausted
- Repeated stall
- Mandatory check unfulfillable

### Blocked vs. Independent Work
- Failed findings block dependent tasks.
- Independent work continues within the approved scope.
- On interruption: save state, not results.

## Integration & Architecture Conformance

### Integration Engineer (Lead or designated)
- Receives reviewed task results from Department Leads.
- Responsible for interfaces, error handling, an executable whole.
- Uses isolated worktrees or clear file ownership for parallel integration.

### Architecture Lead Review
- Compares architecture, domain contracts and actual implementation.
- Re-engages research specialists only for NEW domain questions.

### Final Mandatory Tests (at the integrated whole)
- Integration tests
- End-to-end tests
- Security tests (if in scope)
- Performance tests (if budgeted)
- Every other approved `required_checks`

A green subpackage is not proof of a working whole. A missing test suite is a
failed check, never a pass.

### Review Invalidation
- Any integration change affecting previously reviewed code invalidates the
  affected reviews.
- Re-run affected checks and an independent re-review.

## Final Report

Delivered at the iteration approval gate:
- Working result / demo
- Exact revision (Git SHA)
- Fulfilled acceptance criteria
- Actual test results (commands, outputs)
- Review independence evidence (session ids, agents, tokens)
- Open risks
- Roles, skills, models used
- Measured effort (tokens, time, agent count)

No fabricated metrics. No claimed token savings without comparison data.
