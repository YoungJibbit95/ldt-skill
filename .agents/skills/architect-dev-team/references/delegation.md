# Adaptive delegation

Roles are responsibilities, not a roster to launch. The orchestrator owns scope,
approval, integration, state, and reporting. Workers cannot approve or expand scope.

| Profile | Normal approach | Review |
| --- | --- | --- |
| Lean | Main agent, one slice, short design | Labeled self-review; delegate only for material risk |
| Balanced | Delegate bounded useful investigation or implementation | One independent review for substantial changes when supported |
| Rigorous | Separate relevant design, implementation, test/security work | Mandatory independent review for high-risk scope; disclose absence and obtain human disposition |

All profiles retain approval gates. Respect runtime concurrency limits; inherit
the active model/reasoning by default. Escalate reasoning for a concrete difficulty
only when supported. Apply explicit token/time budgets only if the tool supports
them; otherwise bound task scope/output. Don't invent budget APIs or cost savings.

Select roles as needed: Architecture (boundaries/tradeoffs); Implementation (one
approved slice); Testing (acceptance/regressions); Security (applicable trust,
auth, secrets, permissions, dependencies); Code Review (actual diff and defects);
Integration (contracts/conflicts); Documentation (affected usage/decisions).
Routine edits don't justify a broad security scan or a permanent agent team.

## Compact task contract

```text
Role / single outcome:
Approved architecture version / milestone:
Repository root / base revision:
Read these paths and facts:
Write ownership (exact paths, or read-only):
Constraints / prohibited side effects:
Acceptance / relevant checks:
Return: paths, changes/findings, commands and outcomes, risks, unresolved items.
Stop: scope ambiguity, ownership conflict, design change, missing permission.
Do not delegate, approve, push, merge, deploy, or install skills.
```

Supply minimum context, using a fresh context if supported. Parallelize independent
reads or disjoint writes. Assign ownership before starting. Shared filesystem
access is not isolation; tests writing caches, fixtures, or databases may also
conflict. Use isolated directories/worktrees when warranted, otherwise sequence.
Don't create user-owned chats for internal workers. Don't delegate recursively.

Wait for relevant results, inspect diffs and evidence, and integrate sequentially.
Don't erase user/worker changes to resolve conflicts. Worker claims alone aren't
completion evidence.

## Independent review and fallback

A reviewer must be a distinct actual agent or human and inspect the final change
with criteria and raw evidence. Don't prime the verdict. Record reviewer identity
and findings. A second prompt to the same agent, role switching, and lint aren't
independent review.

Without available/permitted subagents, use sequential role passes labeled `self`
or `unavailable`. Preserve checks and approval. Mandatory missing independence
needs explicit human disposition, never a claim it happened.
