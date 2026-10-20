# Critic Quality Contract (M2 Slice 2, S2)

A review does not pass because a session existed. The `CriticReport` is a
validated, machine-verifiable contract that binds a review to the revision
it actually reviewed.

## The contract

```json
{
  "task_id": "critic-001",
  "reviewed_task_id": "impl-001",
  "reviewed_revision": "<source snapshot digest>",
  "reviewer": {
    "session_id": "ses_...",
    "agent": "explore",
    "model": "opencode/...",
    "execution_mode": "native",
    "verified": true,
    "read_only_agent": true
  },
  "coverage": {
    "requirements_checked": ["..."],
    "files_inspected": ["src/users.py"],
    "interfaces_checked": ["register()"],
    "evidence_references": ["src/users.py:12"],
    "checks_run": [{"name": "unit-tests", "result": "passed", "evidence": "1 passed"}],
    "unverified_areas": ["concurrency was not exercised"]
  },
  "findings": [
    {"severity": "major", "file": "src/users.py", "line": 12,
     "issue": "the duplicate check is case sensitive",
     "reproduction": "register('A@x.com') then register('a@x.com') both succeed",
     "reference": "acceptance: rejects a duplicate email"}
  ],
  "verified_non_findings": ["invalid addresses are rejected"],
  "confidence": "medium",
  "limitations": ["no concurrency test exists"],
  "recommendation": "approve_with_findings",
  "summary": "One major finding on the duplicate check."
}
```

`summary` is the human-readable handover to the Department Lead. It stays
concise; the raw conversation is not part of the contract.

## What is rejected

| Rejection | Reason |
|-----------|--------|
| no reviewer session id | the review cannot be attributed to a run |
| reviewer session equals the implementer session | the review is not independent |
| `execution_mode` is not `native` | a fixture or simulated run is not a review |
| reviewer session is not verified in the runtime | the session cannot be confirmed |
| reviewer agent is not read-only | the reviewer could have changed production code |
| `reviewed_revision` differs from the current revision | the review is bound to an outdated revision |
| `task_id` or `reviewed_task_id` mismatch | the report belongs to another task |
| no `requirements_checked` or no `files_inspected` | the review shows no coverage |
| a check without evidence | the report claims a result it cannot show |
| a file reference that escapes the project | the report points outside the scope |
| a finding without severity, file or issue | the finding is not actionable |
| a major or blocker finding without reproduction | the finding cannot be confirmed |
| neither a finding nor a verified non-finding | the report says nothing about the work |
| a blocking finding with the recommendation `approve` | a blocker cannot be approved away |
| an invalid confidence or recommendation | the verdict is not one of the allowed values |
| a missing or overlong summary | the handover is missing or unusable |

## Read-only critics

The critic runs under a native read-only agent. The runtime's permission set
for that agent denies the write actions, so it **cannot** create or change
any file. It may still run read-only shell commands, as the native agent set
allows; the write boundary is what matters for a review, and it is enforced
by the runtime, not by a policy sentence.

The M2 Slice 1 promise that a critic may add tests under `tests/critic/` is
withdrawn: a measured run showed the write attempts rejected by the native
permission set.

When a test is missing, the critic describes it in `unverified_areas` and
names it in the recommendation. A separately authorised Test Engineer or
Implementation Agent writes it. The independent critic then reviews the
resulting change without touching production code.

## Model policy

The default is a medium-capability model with Medium reasoning. The lead
raises the effort when the report itself justifies it:

- significant security or architecture risk,
- complex mathematical or domain-specific validation,
- inconclusive evidence,
- low confidence,
- repeated disagreement,
- high-impact defects,
- a report that does not provide sufficient evidence.

Confidence alone is not an escalation signal. The model that actually ran is
recorded in the report and in the contract, and an unavailable provider
produces an honest failure rather than a silent downgrade.

## Two answer forms

A reviewer agent may answer in two forms, and both are accepted:

1. **A JSON object** with the shape above. The core takes the candidate that
   satisfies the contract, so an object planted earlier in the answer cannot
   displace the real report.
2. **A structured Markdown review.** A native reviewer agent usually writes a
   report in prose and tables rather than in JSON. The core then extracts the
   structure itself, with the **contract as the authority**:

   - the requirements that were agreed and that the review mentions,
   - the files the review names,
   - the agreed checks, with the result the reviewer stated for each,
   - the findings the review reported, with their severity and location,
   - the confidence and the verdict the reviewer gave.

A check the reviewer never mentioned stays uncovered, and the ordinary
validation refuses the report. The extraction never invents a passing result:
an unmentioned check is `not_run`, not `passed`.

The extraction is a convenience, not a relaxation. The extracted report goes
through the same validation as a JSON one: the revision binding, the reviewer
evidence, the required checks and the blocker rule all apply unchanged.

### What the reader understands

A native reviewer writes a document, not a record. The reader takes the
structure from the document:

| The reader takes it from | What it is |
|-------------------------|------------|
| the verdict heading or line | the decision: approve, approve_with_findings or reject |
| the findings section | the findings, with the severity the section states |
| the verification section | the result of the agreed check |
| the requirement list | the requirements the reviewer checked |
| the scope list | the files the reviewer inspected |

### What the reader never does

- **It never invents a passing result.** A check the reviewer did not mention
  stays `not_run`, and a `not_run` check refuses the report. A row of a
  requirements table is not a check result, and a count that belongs to
  another check is not this check's result.
- **It never turns a denial into a decision.** "no blocking defects found"
  is not a rejection, "the unit test does not pass" is not a pass, and "not
  all acceptance criteria are met" is not acceptance.
- **It never accepts a remark it cannot read.** If the reviewer named a
  severity the reader cannot make out, the review is refused rather than
  accepted as clean.
- **It never accepts a review that contradicts itself.** A verdict that
  denies defects and a report that states a blocking one is refused.
- **It never rescues a JSON report.** The JSON objects are removed from the
  text before the reader sees it, so a report that names the wrong revision
  is decided by the JSON path and refused there.
- **Two reports that disagree are refused.** A JSON report and a prose review
  with different recommendations cannot both be the review.
- **The prose never rescues a JSON report.** The JSON objects are removed
  from the text before the prose reader sees it, so a report that names the
  wrong revision is decided by the JSON path and refused there.
- **A blocker in the prose refuses a JSON approval.** The prose may add
  findings the JSON report does not carry. A report that approves while the
  review text states a blocking defect contradicts itself and is refused.

### The prompt has a limit

The prompt travels as a command line argument, and an argument has a length
limit. The reviewer therefore receives the result of the reviewed work, not
its raw answer, and a prompt that is still too long is cut before it reaches
the command line. The cut is visible to the agent, so it knows that it is not
seeing everything.

### The task contract is the result

A reviewer that fills in its own task contract produces the structured
result directly: status, changes, findings, evidence, checks, risks and
unresolved. The core reads that record after the run and uses it instead of
the prose. The prose reader is the fallback for an agent that did not fill
the contract in. The validation is the same either way.

## Verification

```sh
python <skill>/scripts/validate.py critic-report ROOT validate --task-id critic-001
```

The stored report is re-validated against its contract, the current source
revision and the runtime session. A report that was accepted once is
re-checked whenever the contract is read, and a report bound to an older
revision is refused.
