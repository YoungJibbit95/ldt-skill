"""
Department Lead orchestration.

A Department Lead is a real native agent that coordinates a bounded set of
specialists. The Python core enforces the boundaries; the lead makes the
decisions.

Flow:
  1. the lead receives an outcome-based assignment
  2. it validates it against the approved architecture
  3. it names missing details, dependencies and risks
  4. it proposes bounded specialist assignments
  5. the core validates the plan and creates the specialist contracts
  6. the core dispatches the specialists as real native agents
  7. the lead inspects the results and the evidence
  8. it accepts or requests bounded corrections
  9. the core returns a validated department handoff

The Master Lead keeps scope, approval and integration authority. The lead
cannot approve, cannot widen the scope and cannot spawn further leads.

Python 3.10+, stdlib only.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any, Optional

from .common import Invalid, relative, digest_file
from .agent_answers import extract_lead_review, extract_specialist_result
from .critic_report import extract_json_object, extract_json_objects_deep
from .runtime import dispatch
from .task_contracts import (
    LeadContract, LeadResult, TaskContract,
    create_implementation_contract, save_contract,
)


MAX_SPECIALISTS = 12
MAX_CONFIDENCE_CHARS = 600


def lead_plan_prompt(contract: LeadContract, architecture: str,
                      roster: list[dict[str, Any]], max_specialists: int) -> str:
    """The prompt that asks the lead for a bounded specialist plan."""
    roster_text = "\n".join(
        f"- {item.get('task_id', '?')}: {item.get('role', '?')} -> {item.get('goal', '?')}"
        for item in roster) or "- (no pre-assigned specialists)"
    return f"""You are the Department Lead for {contract.department or 'this department'}.
You coordinate specialists. You do not approve, integrate or widen the scope.

You are a planner. You cannot write or change any file in this project, and
you must not do the work yourself. Your only output is the plan that tells
the specialists what to do.

## Your answer
Reply with one JSON object and nothing else. No prose before it, no prose
after it, no explanation of your reasoning. The object is your plan.

## Outcome you are responsible for
{contract.outcome}

## Approved architecture (read-only reference)
{architecture[:8000]}

## Available specialist assignments
{roster_text}

## Your job
1. Check the outcome against the approved architecture. If they do not fit,
   say so and stop.
2. Name what is missing: information, dependencies, risks.
3. Assign the specialists. Every assignment needs a bounded goal, the files
   it may write, its acceptance criteria, the checks it must run, a model
   profile and a reviewer.

Return ONLY a JSON object with this exact shape. No prose before or after.

{{
  "validates_against_architecture": true,
  "architecture_conflicts": [],
  "missing_information": [],
  "risks": [],
  "assignments": [
    {{
      "task_id": "<id>",
      "role": "<role>",
      "goal": "<single concrete outcome>",
      "file_ownership": {{"<path>": "<task_id>"}},
      "acceptance": ["<observable criterion>"],
      "required_checks": ["<check name>"],
      "model_profile": "<low|medium|high>",
      "review_assignment": "<critic task id>",
      "skill_pins": []
    }}
  ],
  "plan_summary": "<two to four sentences>"
}}

Rules:
- Assign only the specialists listed in the roster above. The roster is the
  agreement with the Master Lead. Never assign yourself, and never invent a
  specialist that is not in the roster.
- At most {max_specialists} assignments. That is a planning budget, not a
  hard organisational limit; if more are genuinely needed, state why in
  "plan_summary" and keep the number at {max_specialists} for this run.
- File ownership must not overlap between assignments.
- Every assignment needs at least one acceptance criterion and one check.
- You must not delegate to other leads and you must not approve anything.
- Do not implement anything yourself. The specialists do the work.
- If the outcome does not fit the approved architecture, set
  "validates_against_architecture" to false, leave "assignments" empty and
  explain in "architecture_conflicts".

Reply now with the single JSON object described above.
"""


def _compact_result(data: dict[str, Any]) -> dict[str, Any]:
    """The result of a specialist without its raw answer.

    The raw answer of a native agent can be tens of thousands of characters
    of exploration. It is preserved in the evidence, but it does not belong
    in the prompt of the next agent: the prompt travels as an argument and
    has a length limit.
    """
    compact: dict[str, Any] = {}
    for key, value in (data or {}).items():
        if key == "evidence" and isinstance(value, dict):
            compact[key] = {name: str(item)[:200]
                            for name, item in value.items()
                            if name != "raw_output"}
            continue
        if isinstance(value, str) and len(value) > 600:
            compact[key] = value[:600] + " [...]"
            continue
        compact[key] = value
    return compact


def lead_review_prompt(contract: LeadContract, architecture: str,
                        results: list[dict[str, Any]],
                        owned_files: Optional[list[str]] = None) -> str:
    """The prompt that asks the lead to accept or to request corrections."""
    results_text = json.dumps([_compact_result(item) for item in results],
                              indent=2, ensure_ascii=False)[:12000]
    return f"""You are the Department Lead for {contract.department or 'this department'}.
The specialists have returned. Inspect their output and evidence.

## Your answer
Reply with one JSON object and nothing else. No prose before it, no prose
after it.

## Outcome you are responsible for
{contract.outcome}

## Approved architecture (read-only reference)
{architecture[:8000]}

## Specialist results and evidence
{results_text}

## Your job
1. For every specialist, check that the required outputs exist, that the
   contract scope matches, that the required verification evidence is present
   and that the review requirements are satisfied.
2. Accept a specialist only when that holds.
3. For an incomplete or defective deliverable, request a bounded correction.
   Name the target, the reason and the required check. At most
   {contract.max_correction_rounds} correction rounds are allowed in total.

Return ONLY a JSON object with this exact shape. No prose before or after.

{{
  "accepted": true,
  "decisions": [
    {{
      "task_id": "<id>",
      "decision": "<accept|reject>",
      "reason": "<why>",
      "correction": {{"goal": "<what to fix>", "checks": ["<check>"]}}
    }}
  ],
  "unresolved": ["<what stays open>"],
  "escalated": false,
  "summary": "<two to four sentences for the Master Lead>"
}}

Your write frame:
You may change only these files, and only to merge or correct the specialists'
work:
{chr(10).join(f"- {path}" for path in (owned_files or [])) or "- (none)"}
Do not create, rename or delete any other file. Do not change files outside
this frame. If a change outside the frame seems necessary, do not make it:
report it under "unresolved" and let the Master Lead decide.

Rules:
- A correction is allowed only for a concrete, bounded defect. Do not ask for
  work outside the approved scope.
- If a specialist's required evidence is missing, that is a rejection with a
  correction, not an acceptance.
- You cannot approve the milestone. A human approval gate still applies.

Reply now with the single JSON object described above.
"""


PLAN_KEYS = ("assignments", "roster_executed", "roster", "specialists", "tasks",
             "stages", "findings", "summary", "plan", "result", "decisions")


def select_plan_candidate(text: str) -> dict[str, Any]:
    """The object in the answer that carries the plan.

    A lead may answer with an envelope around the plan. Every object in the
    answer, nested ones included, is considered. The one that carries the most
    expected keys wins; a tie keeps the last, because an answer usually ends
    with its result.
    """
    candidates = extract_json_objects_deep(text)
    if not candidates:
        raise Invalid("the lead produced no JSON object")
    scored = [(sum(1 for key in PLAN_KEYS if key in candidate), index, candidate)
               for index, candidate in enumerate(candidates)]
    best = max(score for score, _, _ in scored)
    matching = [candidate for score, _, candidate in scored if score == best]
    return matching[-1]


def parse_json_object(text: str, label: str,
                      required_keys: Optional[list[str]] = None,
                      required_any: Optional[list[str]] = None) -> dict[str, Any]:
    """Parse a JSON object from an agent answer.

    The object may be wrapped in a code fence or preceded by a short remark.
    The content is validated by the caller, so a lenient extraction never
    means a lenient verdict.
    """
    if not (text or "").strip():
        raise Invalid(f"{label} produced no output")
    data = extract_json_object(text, required_keys=required_keys, required_any=required_any)
    if data is None:
        required = required_keys if required_keys is not None else required_any
        raise Invalid(f"{label} output contains no complete JSON object with the "
                      f"required fields {required}")
    return data


LEAD_ROLES = {"department lead", "department_lead", "lead", "master lead"}


def validate_lead_plan(plan: dict[str, Any], contract: LeadContract,
                        roster: list[dict[str, Any]],
                        active_ownership: Optional[dict[str, str]] = None,
                        approved_skills: Optional[list[str]] = None,
                        milestone_checks: Optional[list[str]] = None) -> list[str]:
    """Check the lead's plan against the contract, the roster and the project."""
    errors: list[str] = []
    active_ownership = active_ownership or {}
    approved_skills = approved_skills if approved_skills is not None else []
    milestone_checks = milestone_checks if milestone_checks is not None else []
    if not isinstance(plan.get("validates_against_architecture"), bool):
        errors.append("plan does not state whether it validates against the architecture")
    assignments = plan.get("assignments")
    if not isinstance(assignments, list):
        errors.append("plan has no assignments list")
        return errors
    if len(assignments) > MAX_SPECIALISTS:
        errors.append(f"plan assigns {len(assignments)} specialists, above the hard limit "
                      f"of {MAX_SPECIALISTS}")
    for task_id in (plan.get("unknown_assignments") or []):
        errors.append(f"assignment '{task_id}' is not part of the agreed roster")
    if not assignments and plan.get("validates_against_architecture", True):
        # A plan that fits the architecture must name the specialists. A plan
        # that reports a conflict is blocked instead, and carries no assignment.
        errors.append("the plan assigns no specialist")
    if len(assignments) > contract.max_specialists:
        errors.append(f"plan assigns {len(assignments)} specialists, above the agreed "
                      f"budget of {contract.max_specialists}")
    if not plan.get("validates_against_architecture", False) and assignments:
        errors.append("plan reports an architecture conflict but still assigns specialists")

    known = {str(item.get("task_id")) for item in roster if item.get("task_id")}
    # The roster is the authority: it grants the files a specialist may own.
    # The lead may narrow that grant, never widen it.
    roster_grants: dict[str, str] = {}
    for item in roster:
        if not isinstance(item, dict):
            continue
        for path, owner in (item.get("file_ownership") or {}).items():
            roster_grants[str(path)] = str(owner)

    owned: dict[str, str] = {}
    seen_ids: set[str] = set()
    for assignment in assignments:
        if not isinstance(assignment, dict):
            errors.append("an assignment is not an object")
            continue
        task_id = str(assignment.get("task_id", "") or "")
        if not task_id:
            errors.append("an assignment has no task id")
            continue
        if task_id in seen_ids:
            errors.append(f"assignment '{task_id}' appears twice")
        seen_ids.add(task_id)
        if task_id not in known:
            errors.append(f"assignment '{task_id}' is not part of the agreed roster")
        role = str(assignment.get("role", "") or "").strip().lower()
        if role in LEAD_ROLES:
            errors.append(f"assignment '{task_id}' asks for another lead; a lead may "
                          "not delegate to a lead")
        for pin in assignment.get("skill_pins", []) or []:
            skill_id = str(pin).split("@")[0]
            if skill_id not in approved_skills:
                errors.append(f"assignment '{task_id}' pins the unapproved skill "
                              f"'{skill_id}'")
        for check in assignment.get("required_checks", []) or []:
            if milestone_checks and check not in milestone_checks:
                errors.append(f"assignment '{task_id}' requires the check '{check}' "
                              "which is not in the approved milestone policy")
        if not str(assignment.get("goal", "") or "").strip():
            errors.append(f"assignment '{task_id}' has no goal")
        acceptance = assignment.get("acceptance")
        if not isinstance(acceptance, list) or not acceptance:
            errors.append(f"assignment '{task_id}' has no acceptance criteria")
        checks = assignment.get("required_checks")
        if not isinstance(checks, list) or not checks:
            errors.append(f"assignment '{task_id}' has no required checks")
        if str(assignment.get("model_profile", "") or "") not in ("low", "medium", "high"):
            errors.append(f"assignment '{task_id}' has an invalid model profile")
        if not str(assignment.get("review_assignment", "") or "").strip():
            errors.append(f"assignment '{task_id}' has no reviewer")
        ownership = assignment.get("file_ownership")
        if not isinstance(ownership, dict) or not ownership:
            errors.append(f"assignment '{task_id}' owns no files")
            continue
        for path, owner in ownership.items():
            if owner != task_id:
                errors.append(f"assignment '{task_id}' claims file '{path}' for '{owner}'")
            granted = roster_grants.get(path)
            if granted is None:
                errors.append(f"assignment '{task_id}' claims the file '{path}', which "
                              "the roster does not grant")
            elif granted != task_id:
                errors.append(f"assignment '{task_id}' claims the file '{path}', which "
                              f"the roster grants to '{granted}'")
            try:
                relative(path)
            except Invalid as exc:
                errors.append(f"assignment '{task_id}' claims the unsafe path "
                              f"'{path}': {exc}")
                continue
            if path in owned and owned[path] != task_id:
                errors.append(f"file '{path}' is claimed by '{owned[path]}' and '{task_id}'")
            elif path in active_ownership and active_ownership[path] != task_id:
                errors.append(f"file '{path}' is already owned by the active contract "
                              f"'{active_ownership[path]}'")
            else:
                owned[path] = task_id
    return errors


def _create_specialist_contracts(plan: dict[str, Any], contract: LeadContract,
                                  root: Path,
                                  milestone_checks: Optional[list[str]] = None,
                                  approved_skills: Optional[list[str]] = None
                                  ) -> tuple[list[TaskContract], list[str]]:
    """Turn the lead's assignments into real, validated contracts."""
    created: list[TaskContract] = []
    errors: list[str] = []
    for assignment in plan.get("assignments", []):
        task_id = str(assignment.get("task_id"))
        owner = str(assignment.get("review_assignment") or "")
        implementation = create_implementation_contract(
            task_id=task_id,
            role=str(assignment.get("role", "Specialist")),
            goal=str(assignment.get("goal", "")),
            architecture_version=contract.architecture_version or contract.architecture_sha256,
            milestone_id=contract.milestone_id,
            base_revision=contract.base_revision,
            contract_refs=[],
            input_paths=sorted(assignment.get("file_ownership", {}).keys()),
            dependencies=[],
            allowed_actions=[f"write:{path}" for path in assignment.get("file_ownership", {})],
            file_ownership=dict(assignment.get("file_ownership", {})),
            acceptance=list(assignment.get("acceptance", [])),
            required_checks=list(assignment.get("required_checks", [])),
            skill_pins=list(assignment.get("skill_pins", [])),
            model_profile=str(assignment.get("model_profile", "medium")),
            resource_budget=contract.resource_budget or {"tokens": 50000, "time_seconds": 600},
            review_assignment=owner or None,
            escalation=contract.escalation or ["scope_change", "missing_decision"],
        )
        # The contract must satisfy the repository's own rules before it runs.
        from .task_contracts import validate_contract
        problems = validate_contract(
            implementation, list(milestone_checks or []), list(approved_skills or []))
        if problems:
            errors.extend(f"assignment '{task_id}' produced an invalid contract: {problem}"
                          for problem in problems)
            continue
        save_contract(implementation, root)
        from .task_contracts import record_contract_in_state
        record_contract_in_state(root, task_id)
        created.append(implementation)
    return created, errors


def _run_specialist(root: Path, contract: TaskContract) -> dict[str, Any]:
    """Run one specialist as a real native agent and return its result.

    The files the specialist changed are checked against its own ownership.
    A write outside it is recorded as a violation, not as a success.
    """
    before = _tree_state(root)
    run = dispatch(
        prompt=_specialist_prompt(contract),
        role=contract.role,
        cwd=root,
        model_profile=contract.model_profile,
        title=f"ldt {contract.task_id}",
    )
    if run.status != "completed":
        return {
            "task_id": contract.task_id,
            "status": "failed",
            "session_id": run.session_id,
            "agent": run.agent,
            "model": run.model,
            "execution_mode": run.evidence.get("execution_mode", "native"),
            "error": run.error,
            "changes": [], "acceptance_met": False,
            "evidence": {}, "checks": [], "frame_violations": [],
        }
    # The task contract belongs to the specialist: filling it in is part of
    # its task and not a write outside its frame.
    allowed = list(contract.file_ownership or {})
    allowed.append(f".architect-dev-team/tasks/{contract.task_id}.json")
    allowed.append(f".architect-dev-team/tasks/{contract.task_id}.md")
    outside = _outside_frame(before, _tree_state(root), allowed)
    data = _parse_specialist_output(run.output)
    # The specialist filled in its own contract. That record is the result.
    record = _read_task_record(root, contract.task_id)
    if record:
        data = _merge_task_record(data, record)
    data.update({
        "task_id": contract.task_id,
        "session_id": run.session_id,
        "agent": run.agent,
        "model": run.model,
        "execution_mode": run.evidence.get("execution_mode", "native"),
        "model_fallbacks": run.evidence.get("model_fallbacks", []),
        "model_requested_profile": run.evidence.get("model_requested_profile"),
        "frame_violations": outside,
    })
    if outside:
        # The specialist changed something it does not own.
        data["status"] = "failed"
        data["acceptance_met"] = False
    return data


def _specialist_prompt(contract: TaskContract) -> str:
    return f"""You are the {contract.role} for task {contract.task_id}.

## Goal
{contract.goal}

## Files you own and may write
{chr(10).join(f"- {path}" for path in (contract.file_ownership or {})) or "- (none)"}

## Acceptance criteria
{chr(10).join(f"- {a}" for a in (contract.acceptance or [])) or "- (none given)"}

## Checks you must run
{chr(10).join(f"- {c}" for c in (contract.required_checks or [])) or "- (none given)"}

## Rules
- Work only inside the files you own and the acceptance criteria.
- Run the checks and report the real output.
- Do not delegate. Do not approve. Do not push, merge or deploy.
- Report honestly: if something is not done, say so.

Return ONLY a JSON object with this exact shape. No prose before or after.

{{
  "status": "<completed|failed|blocked>",
  "changes": [{{"path": "<path>", "action": "<created|modified|deleted>"}}],
  "acceptance_met": true,
  "findings": ["<what you noticed>"],
  "evidence": {{"<check name>": "<the actual output>"}},
  "checks": [{{"name": "<check name>", "result": "<passed|failed|not_run>", "evidence": "<output>"}}],
  "risks": ["<risk>"],
  "unresolved": ["<what stays open>"],
  "summary": "<two to four sentences>"
}}
"""


def _parse_specialist_output(text: str) -> dict[str, Any]:
    try:
        data = parse_json_object(text, "specialist")
    except Invalid:
        # A native specialist answers with prose. The structure is extracted
        # from its own words, and the source is recorded so a reader can tell
        # a reported field from an extracted one.
        data = extract_specialist_result(text)
        data.setdefault("evidence", {})
        if isinstance(data.get("evidence"), dict):
            data["evidence"].setdefault("raw_output", (text or "")[:2000])
        if not data.get("summary"):
            data["summary"] = "the specialist reported in prose; the structure was extracted"
        return data
    data.setdefault("status", "completed")
    data.setdefault("changes", [])
    data.setdefault("acceptance_met", False)
    data.setdefault("findings", [])
    data.setdefault("evidence", {})
    data.setdefault("checks", [])
    data.setdefault("risks", [])
    data.setdefault("unresolved", [])
    data.setdefault("summary", "")
    return data


TOP_LEVEL_SKIP = {".git", "node_modules", ".venv", "venv", "dist", "build",
                  ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox"}
ANYWHERE_SKIP = {"__pycache__"}


def _read_task_record(root: Path, task_id: str) -> dict[str, Any]:
    """The result an agent recorded in its own task contract.

    An agent fills in the contract it was given. That record is more
    reliable than reading the result back out of the agent's prose, so the
    core prefers it. A contract that still holds the template is not a
    result.
    """
    path = root / ".architect-dev-team" / "tasks" / f"{task_id}.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    if str(data.get("status", "") or "") in ("", "created"):
        return {}
    return data


def _merge_task_record(data: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    """The agent's own record wins over the extracted answer."""
    merged = dict(data)
    for field in ("status", "changes", "findings", "evidence", "checks",
                  "risks", "unresolved", "review_notes"):
        value = record.get(field)
        if value in (None, "", [], {}):
            continue
        merged[field] = value
    merged["result_source"] = "task_contract"
    return merged

def _tree_state(root: Path) -> dict[str, str]:
    """A content digest per file under the project root.

    The managed state directory is deliberately NOT skipped: the lead must
    never change the approval state. A skip list that hid it would leave the
    gate open for a forged approval.

    The cache directories a tool creates are skipped: they are not part of
    the project, and a read-only agent that runs the test suite creates
    them.
    """
    state: dict[str, str] = {}
    for path in root.rglob("*"):
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        parts = relative.parts
        if parts and parts[0] in TOP_LEVEL_SKIP:
            continue
        if any(part in ANYWHERE_SKIP for part in parts):
            continue
        if not path.is_file() or path.is_symlink():
            continue
        try:
            state[relative.as_posix()] = digest_file(path)
        except OSError:
            continue
    return state


def _outside_frame(before: dict[str, str], after: dict[str, str],
                   owned_files: list[str]) -> list[str]:
    """The files that changed outside the lead's write frame."""
    allowed = set(owned_files or [])
    changed = set()
    for path, digest in after.items():
        if before.get(path) != digest:
            changed.add(path)
    for path in before:
        if path not in after:
            changed.add(path)
    return sorted(path for path in changed if path not in allowed)


CONTRACT_KEYS = ("assignment", "contract", "task_contract", "spec", "details",
                 "acceptance_criteria", "criteria")


def _all_task_ids(node: Any, found: Optional[list[str]] = None) -> list[str]:
    """Every task id the plan names, wherever it names them."""
    if found is None:
        found = []
    if isinstance(node, dict):
        task_id = node.get("task_id")
        if isinstance(task_id, str) and task_id and task_id not in found:
            found.append(task_id)
        for value in node.values():
            _all_task_ids(value, found)
    elif isinstance(node, list):
        for item in node:
            _all_task_ids(item, found)
    return found


def _find_assignment_dicts(node: Any, known_ids: set[str],
                            found: list[dict[str, Any]]) -> None:
    """Collect every dict in the plan that names a known task id."""
    if isinstance(node, dict):
        task_id = node.get("task_id")
        if isinstance(task_id, str) and task_id in known_ids:
            found.append(node)
        for value in node.values():
            _find_assignment_dicts(value, known_ids, found)
    elif isinstance(node, list):
        for item in node:
            _find_assignment_dicts(item, known_ids, found)


def _first_text(node: Any, keys: tuple[str, ...]) -> str:
    if not isinstance(node, dict):
        return ""
    for key in keys:
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _normalise_plan(plan: dict[str, Any], roster: Optional[list[dict[str, Any]]] = None
                     ) -> dict[str, Any]:
    """Bring the lead's answer into the shape the core validates.

    The assignments are found by their task id wherever the lead put them.
    The gaps are filled from the agreed roster, which is the authority. The
    result is then validated strictly.
    """
    if not isinstance(plan, dict):
        return {}
    normalised = dict(plan)
    roster = roster or []
    known = {str(item.get("task_id")) for item in roster if item.get("task_id")}
    roster_by_id = {str(item.get("task_id")): item for item in roster if item.get("task_id")}

    found: list[dict[str, Any]] = []
    _find_assignment_dicts(plan, known, found)

    # An assignment the lead invented is not silently dropped. It is carried
    # through so the validation can refuse it.
    unknown: list[str] = []
    for item in _all_task_ids(plan):
        if item not in known and item not in unknown:
            unknown.append(item)

    assignments: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in found:
        task_id = str(item.get("task_id"))
        if task_id in seen:
            continue
        seen.add(task_id)
        entry = dict(item)
        # Details may sit in a nested contract object.
        for key in CONTRACT_KEYS:
            nested = item.get(key)
            if isinstance(nested, dict):
                for field, value in nested.items():
                    entry.setdefault(field, value)
        base = roster_by_id.get(task_id, {})
        # The roster is the base; the lead's answer refines it. A field the
        # lead leaves empty keeps the agreed value.
        entry = dict(base)
        for field, value in item.items():
            if value not in (None, "", [], {}):
                entry[field] = value
        entry["task_id"] = task_id
        entry.setdefault("role", "Specialist")
        entry.setdefault("goal", "")
        ownership = entry.get("file_ownership")
        if not isinstance(ownership, dict) or not ownership:
            ownership = {}
            files = entry.get("files") or entry.get("writes") or []
            if isinstance(files, list):
                for item in files:
                    if isinstance(item, str):
                        ownership[item] = task_id
                    elif isinstance(item, dict) and item.get("path"):
                        ownership[str(item["path"])] = task_id
            entry["file_ownership"] = ownership
        acceptance = entry.get("acceptance")
        if not isinstance(acceptance, list) or not acceptance:
            acceptance = entry.get("acceptance_criteria") or []
            acceptance = [str(item.get("criterion")) if isinstance(item, dict) else str(item)
                          for item in acceptance if item]
            entry["acceptance"] = acceptance
        checks = entry.get("required_checks")
        if not isinstance(checks, list) or not checks:
            checks = entry.get("checks") or []
            checks = [str(item.get("name")) if isinstance(item, dict) else str(item)
                      for item in checks if item]
            entry["required_checks"] = checks
        entry.setdefault("model_profile", "medium")
        entry.setdefault("review_assignment", "")
        entry.setdefault("skill_pins", [])
        assignments.append(entry)

    if not assignments and roster:
        # The lead organises the agreed specialists. When its answer names
        # none, the roster the Master Lead agreed supplies them.
        for item in roster:
            task_id = str(item.get("task_id", ""))
            if not task_id:
                continue
            entry = dict(item)
            entry.setdefault("role", "Specialist")
            entry.setdefault("goal", "")
            entry.setdefault("file_ownership", {})
            entry.setdefault("acceptance", [])
            entry.setdefault("required_checks", [])
            entry.setdefault("model_profile", "medium")
            entry.setdefault("review_assignment", "")
            entry.setdefault("skill_pins", [])
            assignments.append(entry)

    normalised["assignments"] = assignments
    normalised["unknown_assignments"] = unknown
    conflicts = normalised.get("architecture_conflicts") or []
    if conflicts:
        # A listed conflict wins over the lead's own boolean.
        normalised["validates_against_architecture"] = False
    elif "validates_against_architecture" not in normalised:
        normalised["validates_against_architecture"] = True
    if "plan_summary" not in normalised:
        normalised["plan_summary"] = _first_text(plan, ("plan_summary", "summary",
                                                        "plan", "status_summary")) or ""
    return normalised


def _acceptance_holds(results: list[dict[str, Any]],
                      required_checks: Optional[list[str]] = None) -> bool:
    """True when every specialist met its acceptance criteria with evidence.

    The raw answer is preserved for the reader, but it is not evidence. A
    placeholder check object and a failed check are not evidence either, and
    the checks the milestone agreed have to be reported.
    """
    if not results:
        return False
    required = [str(name) for name in (required_checks or [])]
    for item in results:
        if item.get("status") != "completed":
            return False
        if not item.get("acceptance_met"):
            return False
        checks = [check for check in (item.get("checks") or [])
                  if isinstance(check, dict)]
        passed = [check for check in checks if check.get("result") == "passed"]
        evidence = item.get("evidence")
        if not isinstance(evidence, dict):
            evidence = {}
        reported = {key: value for key, value in evidence.items()
                    if key != "raw_output" and value}
        if not reported and not passed:
            return False
        if required:
            named = {str(check.get("name")) for check in checks}
            for name in required:
                if name not in named and name not in reported:
                    return False
    return True


def _active_ownership(root: Path) -> dict[str, str]:
    """The file ownership held by the contracts that are still open."""
    tasks_dir = root / ".architect-dev-team" / "tasks"
    owned: dict[str, str] = {}
    if not tasks_dir.is_dir():
        return owned
    for path in tasks_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if data.get("status") in (None, "created", "in_progress"):
            for file_path, owner in (data.get("file_ownership") or {}).items():
                owned.setdefault(file_path, str(owner))
    return owned


def _approved_skills(root: Path) -> list[str]:
    """The skills the project has approved.

    A skill that the project has not recorded as approved is refused. The
    record lives in the project state, because the approval is a decision of
    the project and not of the registry.
    """
    state_path = root / ".architect-dev-team" / "state.json"
    if not state_path.exists():
        return []
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []
    approved = state.get("approved_skills")
    if not isinstance(approved, list):
        return []
    return [str(item) for item in approved if item]


def run_department_lead(root: Path, contract: LeadContract,
                        roster: Optional[list[dict[str, Any]]] = None,
                        architecture: str = "") -> LeadResult:
    """Coordinate a department and return a validated handoff."""
    roster = roster or contract.specialist_roster or []
    result = LeadResult(lead_task_id=contract.task_id, status="completed")

    # The architecture the lead plans against must be the approved one.
    if contract.architecture_path and contract.architecture_sha256:
        candidate = root / contract.architecture_path
        if candidate.exists():
            from .common import digest_file
            actual = digest_file(candidate)
            if actual != contract.architecture_sha256:
                result.status = "blocked"
                result.escalated = True
                result.unresolved.append(
                    f"the architecture file changed: {actual} does not match the "
                    f"approved {contract.architecture_sha256}")
                return result

    # --- 1. the lead plans -------------------------------------------
    # The plan phase runs under the native read-only agent. The lead may read
    # and plan here, but it cannot implement the work itself, so the
    # specialists really do the implementation.
    plan_before = _tree_state(root)
    plan_run = dispatch(
        prompt=lead_plan_prompt(contract, architecture, roster, contract.max_specialists),
        role="department_lead",
        cwd=root,
        model_profile=contract.model_profile,
        title=f"ldt {contract.task_id} plan",
        agent="plan",
    )
    # The plan phase runs under a read-only agent, and the core checks it:
    # a planning run that changed a file did not plan, it implemented.
    plan_writes = _outside_frame(plan_before, _tree_state(root), [])
    if plan_writes:
        result.status = "failed"
        result.escalated = True
        result.evidence.setdefault("trail", []).append(
            {"outcome": "plan_phase_wrote", "files": plan_writes})
        result.unresolved.extend(
            f"the planning run changed '{path}', which a read-only planner may not do"
            for path in plan_writes)
        return result
    if plan_run.status != "completed":
        result.status = "failed"
        result.escalated = True
        result.unresolved.append(f"lead planning run did not complete: {plan_run.error}")
        result.evidence["plan_session_id"] = plan_run.session_id
        return result
    result.evidence["plan_session_id"] = plan_run.session_id
    result.evidence["plan_agent"] = plan_run.agent
    result.evidence["plan_model"] = plan_run.model

    try:
        plan = select_plan_candidate(plan_run.output)
    except Invalid as exc:
        # The answer carried no usable plan. Ask again in the same session,
        # where the context is already there.
        retry = dispatch(
            prompt=("Your previous answer did not contain the plan object. Reply now "
                    "with ONLY the JSON object, starting with { and ending with }. "
                    "No prose, no code fence."),
            role="department_lead",
            cwd=root,
            model_profile=contract.model_profile,
            title=f"ldt {contract.task_id} plan",
            session_id=plan_run.session_id,
            agent="plan",
        )
        result.evidence["plan_retry_session_id"] = retry.session_id
        retry_writes = _outside_frame(plan_before, _tree_state(root), [])
        if retry_writes:
            result.status = "failed"
            result.escalated = True
            result.evidence.setdefault("trail", []).append(
                {"outcome": "plan_phase_wrote", "files": retry_writes})
            result.unresolved.extend(
                f"the planning retry changed '{path}', which a read-only planner "
                "may not do" for path in retry_writes)
            return result
        if retry.status != "completed":
            result.status = "failed"
            result.escalated = True
            result.unresolved.append(f"{exc}; the retry did not complete either")
            return result
        try:
            plan = select_plan_candidate(retry.output)
        except Invalid as retry_exc:
            result.status = "failed"
            result.escalated = True
            result.unresolved.append(str(retry_exc))
            return result

    plan = _normalise_plan(plan, roster)
    # A reported architecture conflict blocks the run before any assignment is
    # checked. A blocked plan is a different outcome from an invalid one.
    if not plan.get("validates_against_architecture", True):
        result.status = "blocked"
        result.escalated = True
        result.unresolved.extend(
            str(item) for item in (plan.get("architecture_conflicts") or []))
        if not result.unresolved:
            result.unresolved.append(
                "the lead reported that the outcome does not fit the approved architecture")
        result.summary = str(plan.get("plan_summary", "") or "")
        result.evidence["missing_information"] = plan.get("missing_information", [])
        result.evidence["risks"] = plan.get("risks", [])
        return result

    plan_errors = validate_lead_plan(
        plan, contract, roster,
        active_ownership=_active_ownership(root),
        approved_skills=_approved_skills(root),
        milestone_checks=list(contract.required_checks or []))
    if plan_errors:
        result.status = "failed"
        result.escalated = True
        result.unresolved.extend(plan_errors)
        result.summary = str(plan.get("plan_summary", "") or "")
        return result

    result.evidence["missing_information"] = plan.get("missing_information", [])
    result.evidence["risks"] = plan.get("risks", [])

    # --- 2. the core creates the specialist contracts -------------------
    specialists, contract_errors = _create_specialist_contracts(
        plan, contract, root,
        milestone_checks=list(contract.required_checks or []),
        approved_skills=_approved_skills(root))
    if contract_errors:
        result.status = "failed"
        result.escalated = True
        result.unresolved.extend(contract_errors)
        result.summary = str(plan.get("plan_summary", "") or "")
        return result

    # --- 3. the specialists run ----------------------------------------
    results = [_run_specialist(root, specialist) for specialist in specialists]
    result.specialists = results

    # The lead's write frame is the union of the specialists' ownership.
    owned_files: list[str] = []
    for specialist in specialists:
        for path in (specialist.file_ownership or {}):
            if path not in owned_files:
                owned_files.append(path)

    # --- 4. the lead reviews and accepts or corrects -------------------
    rounds_used = 0
    frame_violations: list[str] = []
    while True:
        # The review phase may merge the specialists' results. The write
        # frame is the union of the files the specialists own. Remember the
        # tree so the lead's own changes can be checked against that frame.
        before = _tree_state(root)
        review_run = dispatch(
            prompt=lead_review_prompt(contract, architecture, results, owned_files),
            role="department_lead",
            cwd=root,
            model_profile=contract.model_profile,
            title=f"ldt {contract.task_id} review",
        )
        if review_run.status != "completed":
            result.status = "failed"
            result.escalated = True
            result.unresolved.append(f"lead review run did not complete: {review_run.error}")
            return result
        result.evidence.setdefault("review_sessions", []).append(review_run.session_id)
        try:
            review = parse_json_object(review_run.output, "lead review", required_keys=[
                "accepted", "decisions", "summary"])
        except Invalid as exc:
            # A native lead answers with prose as well. The extraction names
            # the specialist it decided on; a review without a decision is
            # refused like a review without a JSON object.
            review = extract_lead_review(
                review_run.output,
                [str(item.get("task_id", "")) for item in roster
                 if item.get("task_id")])
            if not review.get("decisions"):
                result.status = "failed"
                result.escalated = True
                result.unresolved.append(str(exc))
                return result

        # The lead may only change the files the specialists own.
        after = _tree_state(root)
        # The lead fills in its own task contract. That is part of its task
        # and not a write outside the frame.
        frame = list(owned_files)
        frame.append(f'.architect-dev-team/tasks/{contract.task_id}.json')
        frame.append(f'.architect-dev-team/tasks/{contract.task_id}.md')
        outside = _outside_frame(before, after, frame)
        if outside:
            frame_violations.extend(outside)
            result.evidence.setdefault("trail", []).append(
                {"outcome": "write_frame_violated", "files": outside})
            result.escalated = True
            result.status = "escalated"
            result.unresolved.extend(
                f"the lead changed '{path}', which is outside its write frame"
                for path in outside)
            break

        decisions = review.get("decisions") or []
        corrections = []
        for decision in decisions:
            if not isinstance(decision, dict):
                continue
            if str(decision.get("decision", "")) == "reject":
                corrections.append(decision)
        result.corrections.extend(corrections)
        result.unresolved.extend(str(item) for item in (review.get("unresolved") or []))
        result.escalated = bool(review.get("escalated", False)) or result.escalated
        result.summary = str(review.get("summary", "") or "")[:MAX_CONFIDENCE_CHARS]

        # The core decides. A specialist that failed its acceptance criteria or
        # produced no evidence is never accepted, whatever the lead said.
        result.accepted = (bool(review.get("accepted", False))
                           and _acceptance_holds(results,
                                                list(contract.required_checks or [])))

        if not corrections or rounds_used >= contract.max_correction_rounds:
            break

        # --- 5. bounded correction rounds --------------------------------
        # One round may not consume more corrections than the budget allows.
        if len(corrections) > contract.max_correction_rounds:
            result.evidence.setdefault("trail", []).append(
                {"outcome": "repair_budget_exhausted",
                 "rounds": contract.max_correction_rounds})
            result.escalated = True
            break
        for decision in corrections:
            target = str(decision.get("task_id", ""))
            specialist = next((s for s in specialists if s.task_id == target), None)
            if specialist is None:
                continue
            rounds_used += 1
            goal = str((decision.get("correction") or {}).get("goal", "") or "")
            checks = list((decision.get("correction") or {}).get("checks", []) or [])
            corrected_contract = _corrected_contract(specialist, goal, checks)
            # A correction may not smuggle in a check outside the policy.
            from .task_contracts import validate_contract
            problems = validate_contract(
                corrected_contract, list(contract.required_checks or []),
                list(_approved_skills(root)))
            if problems:
                result.evidence.setdefault("trail", []).append(
                    {"outcome": "invalid_correction", "problems": problems})
                result.escalated = True
                break
            corrected = _run_specialist(root, corrected_contract)
            results = [corrected if r.get("task_id") == target else r for r in results]
        result.rounds_used = rounds_used

    if result.escalated:
        result.status = "escalated"
    result.evidence["rounds_used"] = rounds_used
    if not result.accepted:
        # The deliverable was not accepted. The core escalates, whatever the
        # lead reported.
        result.escalated = True
        if result.status == "completed":
            result.status = "escalated"
        if rounds_used >= contract.max_correction_rounds:
            result.unresolved.append(
                f"the correction budget of {contract.max_correction_rounds} rounds is "
                "spent and the deliverable is not accepted")
    return result


def _corrected_contract(contract: TaskContract, goal: str,
                         checks: list[str]) -> TaskContract:
    """A bounded correction contract for the same owner and files."""
    corrected = TaskContract(
        task_id=contract.task_id,
        role=contract.role,
        goal=goal or contract.goal,
        architecture_version=contract.architecture_version,
        milestone_id=contract.milestone_id,
        base_revision=contract.base_revision,
        contract_refs=list(contract.contract_refs),
        input_paths=list(contract.input_paths),
        dependencies=list(contract.dependencies),
        allowed_actions=list(contract.allowed_actions),
        file_ownership=dict(contract.file_ownership),
        acceptance=list(contract.acceptance),
        required_checks=list(checks) or list(contract.required_checks),
        skill_pins=list(contract.skill_pins),
        model_profile=contract.model_profile,
        resource_budget=dict(contract.resource_budget),
        review_assignment=contract.review_assignment,
        escalation=list(contract.escalation),
    )
    return corrected


def lead_execution_cli(root: Path, command: str, **kwargs) -> int:
    try:
        if command != "run-lead":
            print(f"Unknown command: {command}", file=sys.stderr)
            return 1
        from .task_contracts import load_contract
        contract = load_contract(root, kwargs["lead_task_id"])
        if not hasattr(contract, "outcome"):
            print(f"INVALID: {kwargs['lead_task_id']} is not a lead contract", file=sys.stderr)
            return 1
        architecture = ""
        arch_path = getattr(contract, "architecture_path", "")
        if arch_path:
            candidate = root / arch_path
            if candidate.exists():
                architecture = candidate.read_text(encoding="utf-8")
        roster = list(getattr(contract, "specialist_roster", []) or [])
        roster_path = kwargs.get("roster")
        if roster_path:
            from pathlib import Path as _P
            loaded = json.loads(_P(roster_path).read_text(encoding="utf-8"))
            if not isinstance(loaded, list):
                raise Invalid("the roster file must contain a list of assignments")
            roster = loaded
        result = run_department_lead(root, contract, roster, architecture)
        payload = result.to_dict()
        out = root / ".architect-dev-team" / "lead_result.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"lead result -> {out}")
        print(f"status={result.status} accepted={result.accepted} "
              f"rounds={result.rounds_used} escalated={result.escalated}")
        for unresolved in result.unresolved:
            print(f"  - {unresolved}")
        return 0 if result.accepted and not result.escalated else 1
    except Invalid as e:
        print(f"INVALID: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"INVALID: {e}", file=sys.stderr)
        return 1
