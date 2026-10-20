# Task Contract Specification

Every implementation and review task receives a detailed contract.
Contracts are versioned, bound to architecture, and contain all execution parameters.

## Contract Schema (Required Fields)

```json
{
  "task_id": "impl-001",
  "role": "Backend Specialist",
  "goal": "Single concrete outcome description",
  "architecture_version": "v1.2",
  "milestone_id": "M1",
  "base_revision": "abc123...",
  "contract_refs": ["contract-api-001", "contract-db-001"],
  "input_paths": ["src/api/", "specs/openapi.yaml"],
  "dependencies": ["research-001", "task-contract-002"],
  "allowed_actions": ["write:src/api/**", "read:specs/**"],
  "file_ownership": {"src/api/users.py": "impl-001"},
  "acceptance": ["POST /users returns 201", "validation rejects invalid email"],
  "required_checks": ["unit-tests", "contract-test"],
  "skill_pins": ["fastapi@49f948f"],
  "model_profile": "medium",
  "resource_budget": {"tokens": 50000, "time_seconds": 300},
  "review_assignment": "critic-001",
  "escalation": ["scope_change", "missing_decision", "security_risk", "budget_exceeded", "repair_exhausted"]
}
```

## Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Unique stable ID: `impl-<nnn>`, `critic-<nnn>`, `integration-<nnn>` |
| `role` | string | Specialist role: Backend, Frontend, Domain, Security, Integration, QA, Docs |
| `goal` | string | Single concrete outcome, not a process description |
| `architecture_version` | string | Exact architecture version this task implements |
| `milestone_id` | string | Milestone ID from architecture (M1, M2, ...) |
| `base_revision` | string | Git commit SHA at task creation (for drift detection) |
| `contract_refs` | string[] | IDs of interface/data contracts this task must honor |
| `input_paths` | string[] | Paths the task may read (globs allowed) |
| `dependencies` | string[] | Task IDs that must complete before this starts |
| `allowed_actions` | string[] | Permission globs: `read:path/**`, `write:path/**`, `exec:command` |
| `file_ownership` | object | Exact path → task_id mapping; prevents conflicts |
| `acceptance` | string[] | Observable acceptance criteria (testable) |
| `required_checks` | string[] | Stable check names from milestone.required_checks |
| `skill_pins` | string[] | Exact skill IDs@revision required for this task |
| `model_profile` | string | `low` / `medium` / `high` — maps to available model variants |
| `resource_budget` | object | Token limit, time limit, concurrency limit |
| `review_assignment` | string | Critic task_id assigned to review this task |
| `escalation` | string[] | Conditions that stop work and escalate to Lead |

## Critic Contract (Additional Fields)

```json
{
  "task_id": "critic-001",
  "role": "Independent Critic",
  "goal": "Verify implementation against requirements and find defects",
  "review_target": "impl-001",
  "independence": "unavailable",  // proven by runtime evidence, never declared
  "review_criteria": ["requirements_coverage", "error_scenarios", "security_boundaries", "performance_budgets"],
  "allowed_actions": ["read:src/**", "read:tests/**", "exec:pytest"],
  "prohibited_actions": ["write:src/**", "write:production/**", "write:tests/**"],
  "evidence_requirements": ["file:line references", "reproduction steps", "spec references", "test cases"],
  "critic_report": { "...": "the validated report from the review run" }
}
```

The critic is **read-only**. It cannot create a test file, not even under
`tests/critic/`: the native agent's permission set refuses every write, and
the M2 Slice 1 promise that a critic may add tests is withdrawn. A missing
test is described in the report instead. See
[critic quality](critic-quality.md) for the report contract and the
verification rules.

### Lead Contract (M2 Slice 2)

```json
{
  "task_id": "lead-backend",
  "role": "Department Lead",
  "goal": "Deliver the approved registration store slice",
  "department": "backend",
  "outcome": "Deliver the approved registration store slice",
  "architecture_path": ".architect-dev-team/architecture.md",
  "architecture_sha256": "<digest of the approved architecture>",
  "milestone_id": "M1",
  "base_revision": "<revision>",
  "acceptance": ["the store rejects a duplicate address"],
  "required_checks": ["unit-tests"],
  "resource_budget": {"tokens": 120000, "time_seconds": 900},
  "specialist_roster": [{"task_id": "impl-001", "role": "Backend Specialist", "goal": "..."}],
  "max_specialists": 3,
  "max_correction_rounds": 2,
  "lead_result": { "...": "the validated department handoff" }
}
```

| Field | Meaning |
|-------|---------|
| `department` | the area the lead coordinates |
| `outcome` | the single result the lead is accountable for |
| `architecture_path`, `architecture_sha256` | the approved architecture; the digest is verified before the lead plans |
| `specialist_roster` | the assignments the Master Lead agreed with; the lead may not widen it |
| `max_specialists` | the planning budget; a plan above it is rejected |
| `max_correction_rounds` | the correction budget; exhausting it escalates |
| `lead_result` | the validated handoff returned to the Master Lead |

A `LeadResult` carries the specialist results, the corrections, the rounds
used, the unresolved items and the session evidence. It has **no** approval
field: a department acceptance never replaces the human approval gate.

## Handoff Format (Task Result)

```json
{
  "task_id": "impl-001",
  "status": "completed",  // completed, failed, blocked, escalated
  "changes": [
    {"path": "src/api/users.py", "action": "created", "sha256": "..."},
    {"path": "tests/test_users.py", "action": "created", "sha256": "..."}
  ],
  "findings": ["Implemented user creation endpoint", "Added email validation"],
  "evidence": {
    "unit_tests": "pytest tests/test_users.py -v: 5 passed",
    "contract_test": "pytest tests/contract/test_users.py: 3 passed"
  },
  "checks": [
    {"name": "unit-tests", "status": "passed", "evidence": "5 tests passed"},
    {"name": "contract-test", "status": "passed", "evidence": "3 contract tests passed"}
  ],
  "risks": ["Validation logic may need refinement for edge cases"],
  "unresolved": [],
  "review_notes": "Ready for critic-001"
}
```

## Critic Result

```json
{
  "task_id": "critic-001",
  "status": "completed",
  "review_target": "impl-001",
  "independence": "independent",
  "findings": [
    {"severity": "blocker", "file": "src/api/users.py", "line": 42, "issue": "Missing duplicate email check", "reproduction": "POST /users with same email twice returns 201 both times", "reference": "acceptance: validation rejects invalid email"},
    {"severity": "major", "file": "tests/test_users.py", "line": 15, "issue": "Test doesn't cover invalid email format", "reproduction": "Run test with malformed email - passes incorrectly"},
    {"severity": "minor", "file": "src/api/users.py", "line": 10, "issue": "Missing docstring on public function"}
  ],
  "evidence": {
    "reproduction": "curl -X POST /users -d '{\"email\":\"test@test.com\"}' twice",
    "test_added": "tests/critic/test_duplicate_email.py"
  },
  "checks": [
    {"name": "pair-review", "status": "failed", "evidence": "Blocker found: duplicate email not rejected"}
  ],
  "recommendation": "Repair blocker, then re-review"
}
```

## Contract Lifecycle

1. **Created** by Department Lead from architecture + milestone
2. **Assigned** to specialist (subagent or sequential pass)
3. **Executed** with bounded permissions and resources
4. **Result** produced with evidence and check outcomes
5. **Reviewed** by assigned critic (independent)
6. **Repaired** if findings require (max 2 rounds per finding group)
7. **Accepted** by Department Lead → integration

## Validation Rules

- All required fields present
- `file_ownership` paths don't overlap with other active tasks
- `allowed_actions` don't exceed milestone permissions
- `required_checks` subset of `milestone.required_checks`
- `skill_pins` reference approved, installed skills only
- `base_revision` matches current HEAD at creation
- `review_assignment` points to valid critic contract