# Task Contract: <task_id>

**Role**: <role>
**Goal**: <single concrete outcome>
**Architecture Version**: <version>
**Milestone**: <milestone_id>
**Base Revision**: <git sha>

---

## Contract References
- <contract-id-1>
- <contract-id-2>

## Input Paths (Read Access)
- <path/glob>

## Dependencies
- <task-id-1>
- <task-id-2>

## Permissions
**Allowed Actions**:
- read:<path>/**
- write:<path>/**
- exec:<command>

**File Ownership**:
| Path | Owner |
|------|-------|
| <path> | <task_id> |

## Acceptance Criteria
- <observable criterion 1>
- <observable criterion 2>

## Required Checks
- <check-name-1>
- <check-name-2>

## Skill Pins
- <skill-id>@<revision>

## Model Profile
<low | medium | high>

## Resource Budget
- Tokens: <limit>
- Time: <seconds>
- Concurrency: <max parallel>

## Review Assignment
- Critic: <critic-task-id>

## Escalation Triggers
- scope_change
- missing_decision
- security_risk
- budget_exceeded
- repair_exhausted

---

## Result (Filled at Completion)

**Status**: <completed | failed | blocked | escalated>

**Changes**:
| Path | Action | SHA256 |
|------|--------|--------|
| <path> | <created|modified|deleted> | <hash> |

**Findings**:
- <finding 1>
- <finding 2>

**Evidence**:
- <check>: <command>: <outcome>

**Checks**:
| Name | Status | Evidence |
|------|--------|----------|
| <check> | <passed|failed|waived> | <evidence> |

**Risks**:
- <risk>

**Unresolved**:
- <item>

**Review Notes**: <notes for critic>