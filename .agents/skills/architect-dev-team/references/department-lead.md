# Department Lead Orchestration (M2 Slice 2, S1)

A Department Lead is a real native agent that coordinates a bounded set of
specialists. It is not a role document and it does not run in parallel with
the Master Lead's authority.

## Two sub-phases, two native agents

The lead is not read-only: it has to merge the specialists' results. The
separation between planning and implementing is therefore made structurally.

| Sub-phase | Native agent | May write | Purpose |
|-----------|--------------|-----------|---------|
| plan | `plan` (read-only) | no | validate the outcome, name the gaps, propose the assignments |
| merge | `general` | only the specialists' files | review the results, request corrections, integrate |

A measured run showed the lead doing the implementation itself when it ran
under the writable agent. The plan sub-phase therefore runs read-only, so the
specialists really do the work. The merge sub-phase may change files, and the
core checks afterwards which files actually changed.

### The write frame

The merge sub-phase may only change the files the specialists own. The frame
is the union of their `file_ownership`. The core compares the tree before and
after the merge; a change outside the frame is refused and the handoff is
escalated. The frame is enforced by the core, not only stated in the prompt.

The **roster** grants the files. The lead may narrow a grant, never widen
one: a plan that claims a file the roster does not grant is refused, and the
frame of the merge follows the grant, not the plan.

The **plan sub-phase** may not write at all. The core compares the tree
before and after the planning run; a change there is refused, because a run
that changed a file did not plan.

The **specialists** are checked the same way: the files a specialist changed
are compared with its own `file_ownership`. A write outside it marks the
specialist as failed.

## The eleven steps

| # | Step | Produces | Boundary |
|---|------|----------|----------|
| 1 | Receive an outcome-based assignment | goal, scope, milestone | The lead does not widen the goal |
| 2 | Validate against the approved architecture | confirmed, or a conflict list | A conflict stops the run |
| 3 | Name missing details, dependencies, risks | `missing_information`, `risks` | The lead does not invent facts |
| 4 | Create bounded specialist assignments | contracts with ownership | No overlapping file ownership |
| 5 | Recommend models and skills | per assignment profile | A recommendation, never an installation |
| 6 | Define outputs, contracts, review expectations | acceptance, checks, reviewer | Every assignment needs a reviewer |
| 7 | Delegate to actual native agents | real sessions | The lead never delegates to other leads |
| 8 | Collect specialist results | results with session evidence | A failed run is recorded as failed |
| 9 | Inspect outputs and evidence | accept, or a bounded correction | Missing evidence means rejection |
| 10 | Request bounded corrections | a correction with a goal and checks | At most two rounds in total |
| 11 | Return a validated department handoff | `LeadResult` | The lead does not approve anything |

The plan sub-phase covers the steps 1 to 6, the merge sub-phase the steps 7
to 11.

## The Master's authority

The Master Lead keeps:

- scope and milestone definition,
- the human start, architecture, iteration, installation, merge and
  deployment approval gates,
- the decision to run a department at all.

A Department Lead may recommend a specialist budget above the normal three,
but the Master Lead authorises it. The lead may not create a second
approval state machine, and a department acceptance is not a milestone
approval.

## The specialist budget

Three specialists per Department Lead is the normal planning budget, not a
hard organisational limit. A lead that needs more must state why in its plan
summary, keep the assignment within the agreed budget for that run, and leave
the extension to the Master Lead. Recursive delegation is not possible: the
lead has no mechanism to start another lead.

## The bounded correction loop

1. The lead reviews every specialist result against its contract.
2. A deliverable is accepted only when the required outputs exist, the scope
   matches, the required verification evidence is present, the review
   requirements are satisfied, and no blocking finding is open.
3. An incomplete or defective deliverable produces a correction with a
   concrete goal and the check that must run.
4. The correction runs against the same owner and the same files.
5. After at most two correction rounds, the lead returns the result with the
   unresolved items listed. The lead does not declare success it did not
   achieve.

## The plan shape

**The roster is the authority.** The Master Lead agrees the specialists with
the Department Lead. The lead organises them; it does not invent them.

A lead reports its plan in its own words, possibly wrapped in an envelope. The
core looks for the assignments at any depth, by their task id, and falls back
to the agreed roster when the answer names none. The result is then validated
strictly:

- an assignment outside the roster is refused, not silently dropped,
- a plan that names no assignment while the roster is empty is refused,
- an unsafe path, another lead as assignee, an unapproved skill pin or a
  check outside the milestone policy is refused,
- overlapping ownership with an active contract is refused.

A reported architecture conflict blocks the run before any assignment is
checked: a blocked plan is a different outcome from an invalid one.

The roster entry carries the full specialist definition:

```json
{
  "task_id": "impl-001",
  "role": "Backend Specialist",
  "goal": "Implement the canonical registration store",
  "acceptance": ["register rejects a duplicate address"],
  "required_checks": ["unit-tests"],
  "file_ownership": {"src/registry.py": "impl-001"},
  "model_profile": "medium",
  "review_assignment": "critic-001",
  "skill_pins": []
}
```

## How the lead's answer is read

A lead writes a document. The core reads the decision from the verdict
heading, and the decision on a specialist from the line that names that
specialist and states a decision near it. A decision word far away in a long
narrative belongs to something else and does not decide anything.

A word in a denial does not decide anything either: "no correction round
needed" is not a rejection, and "the store rejects a duplicate address" is a
requirement, not a verdict.

## What the lead is not allowed to do

- approve a milestone or create an approval record,
- install or activate a skill,
- push, merge, deploy or publish,
- assign files that another assignment already owns,
- delegate to another lead,
- report a specialist as successful when its evidence is missing,
- change a file outside the specialists' ownership during the merge.

## Execution evidence

A department handoff is only real when it carries session evidence:

| Field | Meaning |
|-------|---------|
| `plan_session_id` | the session that produced the plan |
| `review_sessions` | the sessions that produced the acceptances |
| `specialists[].session_id` | the session per specialist |
| `specialists[].execution_mode` | `native` or `fixture` |
| `trail[].outcome` | `write_frame_violated` when the lead left its frame |

A run without session evidence is preparation, not execution. The core
records the evidence; it does not infer it from the presence of a file.
