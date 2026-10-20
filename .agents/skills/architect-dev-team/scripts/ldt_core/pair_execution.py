"""
Pair Execution: Dispatches implementer and critic as independent native subagents.

Python 3.10+, stdlib only. Uses the real OpenCode runtime adapter. When the
runtime is unavailable the module reports an honest `unavailable` state and
never fabricates findings or independence.
"""
from __future__ import annotations
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

from .common import Invalid
from .agent_answers import extract_specialist_result
from .lead_execution import _compact_result
from .document_reader import strip_json_objects
from .lead_execution import _merge_task_record, _read_task_record
from .critic_report import (
    CriticReport, extract_json_objects, parse_critic_report,
    parse_critic_report_markdown, report_prompt, validate_critic_report,
)
from .runtime import AgentRun, dispatch, independence_report, verify_session
from .task_contracts import TaskContract, CriticContract, load_contract, save_contract


def dispatch_subagent(root: Path, contract: TaskContract, prompt: str) -> AgentRun:
    """Dispatch a real native OpenCode agent for this contract.

    Uses the contract role to select the native agent. The native agent's own
    permission set enforces the write boundary, so a critic cannot write
    production files even if instructed to.
    """
    run = dispatch(
        prompt=prompt,
        role=contract.role,
        cwd=root,
        model_profile=contract.model_profile,
        title=f"ldt {contract.task_id}",
    )
    # Attach the contract so the agent knows its exact scope.
    run.evidence["task_id"] = contract.task_id
    run.evidence["allowed_actions"] = contract.allowed_actions
    run.evidence["file_ownership"] = contract.file_ownership
    run.evidence.setdefault("execution_mode", "native")
    return run


def _parse_agent_output(run: AgentRun) -> dict[str, Any]:
    """Parse the structured result the agent was asked to return.

    Falls back to an honest record when the agent did not emit JSON.
    """
    text = (run.output or "").strip()
    if not text:
        return {
            "status": "failed" if run.status == "completed" else run.status,
            "changes": [], "findings": [], "evidence": {}, "checks": [],
            "risks": [], "unresolved": [], "review_notes": "",
            "parse_error": "agent produced no text output",
        }
    # Accept a fenced or bare JSON object.
    candidate = text
    if "```" in candidate:
        parts = candidate.split("```")
        for part in parts:
            stripped = part.strip()
            if stripped.startswith("json"):
                stripped = stripped[4:]
            if stripped.startswith("{"):
                candidate = stripped
                break
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        # A native implementer answers with prose. The structure is extracted
        # from its own words; the raw output stays in the evidence.
        extracted = extract_specialist_result(text)
        evidence = extracted.get("evidence")
        if not isinstance(evidence, dict):
            evidence = {}
        evidence.setdefault("raw_output", text[:4000])
        extracted["evidence"] = evidence
        extracted.setdefault("review_notes",
                             "the agent did not return structured JSON; the structure "
                             "was extracted from its answer")
        return extracted
    if not isinstance(data, dict):
        return {
            "status": "completed" if run.status == "completed" else run.status,
            "changes": [], "findings": [], "evidence": {"raw_output": text[:4000]},
            "checks": [], "risks": [], "unresolved": [], "review_notes": "non-object JSON",
        }
    data.setdefault("status", run.status)
    data.setdefault("changes", [])
    data.setdefault("findings", [])
    data.setdefault("evidence", {})
    data.setdefault("checks", [])
    data.setdefault("risks", [])
    data.setdefault("unresolved", [])
    data.setdefault("review_notes", "")
    return data


def run_implementer(root: Path, contract: TaskContract) -> AgentRun:
    """Run the implementer as a real native agent."""
    prompt = f"""You are the {contract.role} for task {contract.task_id}.

## Task Contract
{json.dumps(asdict(contract), indent=2)}

## Acceptance criteria
{chr(10).join(f"- {a}" for a in (contract.acceptance or []))}

## Required checks to run and report
{chr(10).join(f"- {c}" for c in (contract.required_checks or []))}

## Files you own and may write
{chr(10).join(f"- {p}" for p in (contract.file_ownership or {}))}

## Rules
- Implement only inside the contract scope.
- Write the implementation and its tests.
- Run the required checks and report the real command output.
- Do not approve, push, merge, deploy, or install anything.
- Do not create additional subagents.

## Required output
Return ONLY a JSON object with these keys:
status, changes, findings, evidence, checks, risks, unresolved, review_notes
- status: "completed" | "failed" | "blocked" | "escalated"
- changes: list of {{path, action, sha256}}
- findings: list of strings
- evidence: object mapping check name to the actual command output
- checks: list of {{name, status, evidence}}
- risks: list of strings
- unresolved: list of strings
- review_notes: string
"""
    return dispatch_subagent(root, contract, prompt)


def run_critic(root: Path, contract: CriticContract, implementer_result: dict[str, Any],
               revision: str = "", implementer_session_id: str = "") -> AgentRun:
    """Run the critic as a real native agent with its own session.

    The critic receives the requirements, the artifacts under review and the
    implementer's reported result. It does not receive the implementer's
    private reasoning.
    """
    prompt = report_prompt(
        task_id=contract.task_id,
        reviewed_task_id=contract.review_target,
        revision=revision,
        requirements=list(getattr(contract, "requirements", []) or [])
        or ["the acceptance criteria of the reviewed task"],
        files=list(getattr(contract, "files_in_scope", []) or [])
        or ["the files changed by the reviewed task"],
        checks=list(contract.required_checks or []),
        reviewer_session_id="(your own session id is filled in by the runtime)",
        reviewer_agent="(the agent you run under)",
        reviewer_model="(the model you run with)",
        implementation=json.dumps(_compact_result(implementer_result),
                                  indent=2, ensure_ascii=False),
    )
    prompt += f"""

## Review criteria
{chr(10).join(f"- {c}" for c in (contract.review_criteria or []))}

## Evidence you must provide for every finding
{chr(10).join(f"- {e}" for e in (contract.evidence_requirements or []))}

## Rules
- You may READ the project. You must NOT modify any file, not even a test.
- If a test is missing, describe it in "unverified_areas" and recommend it.
- Do not prime your own verdict; judge the artifacts against the criteria.
- Do not approve, push, merge, deploy, or install anything.
- The runtime fills in your session id, agent and model. Leave those fields
  as the placeholders; the orchestrator replaces them with the verified
  values from the runtime.
"""
    return dispatch_subagent(root, contract, prompt)


def repair_loop(
    root: Path,
    impl_contract: TaskContract,
    critic_result: dict[str, Any],
    max_rounds: int = 2,
    critic_contract: Optional[CriticContract] = None,
    revision: str = "",
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run up to max_rounds of targeted repair, re-reviewing after each round.

    Returns the final critic result and the per-round evidence trail.
    """
    trail: list[dict[str, Any]] = []
    if not isinstance(critic_result, dict):
        critic_result = {}
    findings = critic_result.get("findings")
    if not isinstance(findings, list):
        findings = []

    findings_by_group: dict[str, list[Any]] = {}
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        key = finding.get("file", "unknown").split("/")[0] if finding.get("file") else "unknown"
        findings_by_group.setdefault(key, []).append(finding)

    repair_failed = False
    re_review_failed = False
    rounds_used = 0
    # The report and the session that produced it. A re-review replaces both.
    final_report: Optional[dict[str, Any]] = critic_result.get("critic_report")
    final_session: Optional[str] = critic_result.get("session_id")

    for group, group_findings in findings_by_group.items():
        for round_num in range(1, max_rounds + 1):
            if rounds_used >= max_rounds:
                trail.append({"group": group, "outcome": "repair_budget_exhausted",
                              "rounds": rounds_used})
                repair_failed = True
                break
            print(f"Repair round {round_num} for {group}...")
            repair_prompt = f"""Repair exactly these findings from the critic review of {impl_contract.task_id}.

{json.dumps(group_findings, indent=2)}

Change only what these findings require. Do not widen the scope.
Re-run the required checks and report the real output.
Return the same JSON object shape as an implementer result.
"""
            repair_run = dispatch_subagent(root, impl_contract, repair_prompt)
            repair_data = _parse_agent_output(repair_run)
            rounds_used += 1
            trail.append({
                "round": round_num,
                "group": group,
                "implementer_session_id": repair_run.session_id,
                "implementer_agent": repair_run.agent,
                "implementer_model": repair_run.model,
                "status": repair_data.get("status"),
            })
            if repair_run.status != "completed" or repair_data.get("status") != "completed":
                trail[-1]["outcome"] = "repair_not_completed"
                repair_failed = True
                break

            review_contract = critic_contract or CriticContract(
                task_id=f"critic-{impl_contract.task_id}-r{round_num}",
                review_target=impl_contract.task_id,
                architecture_version=impl_contract.architecture_version,
                milestone_id=impl_contract.milestone_id,
                base_revision=impl_contract.base_revision,
                requirements=list(getattr(critic_contract, "requirements", []) or []),
                files_in_scope=list(getattr(critic_contract, "files_in_scope", []) or []),
            )
            re_review = run_critic(root, review_contract, repair_data,
                                   revision=revision,
                                   implementer_session_id=repair_run.session_id or "")
            trail[-1]["critic_session_id"] = re_review.session_id
            trail[-1]["critic_agent"] = re_review.agent
            trail[-1]["critic_model"] = re_review.model

            # The repair changed the tree, so the re-review is bound to the
            # revision that now exists, not to the one before the repair.
            current_revision = _current_revision(root)
            # The re-review must satisfy the same report contract.
            re_report, re_errors = _critic_report_from_run(
                root, re_review, review_contract, repair_run, current_revision)
            if re_errors:
                trail[-1]["report_errors"] = re_errors
                trail[-1]["outcome"] = "re_review_rejected"
                re_review_failed = True
                break

            re_data = _parse_agent_output(re_review)
            re_data["session_id"] = re_review.session_id
            re_data["agent"] = re_review.agent
            re_data["model"] = re_review.model
            if re_report is not None:
                re_data["critic_report"] = re_report.to_dict()
                # The findings of the validated report decide whether the
                # group is resolved. The raw answer is not the review.
                re_data["findings"] = re_report.to_dict().get("findings") or []
                final_report = re_report.to_dict()
                final_session = re_review.session_id
            critic_result = re_data
            remaining = [
                f for f in (re_data.get("findings") or [])
                if isinstance(f, dict) and str(f.get("file", "")).startswith(group)
            ]
            if not remaining:
                trail[-1]["outcome"] = "resolved"
                break
        else:
            trail.append({"group": group, "outcome": "repair_budget_exhausted",
                          "rounds": max_rounds})
            repair_failed = True
            print(f"Max repair rounds ({max_rounds}) reached for {group}. Escalating.")

    if repair_failed or re_review_failed:
        critic_result = dict(critic_result or {})
        critic_result["repair_failed"] = True
    if final_report is not None:
        critic_result["critic_report"] = final_report
    if final_session:
        critic_result["session_id"] = final_session
    return critic_result, trail


def _current_revision(root: Path) -> str:
    """The source revision a review is bound to."""
    import json as _json
    from .common import digest_bytes
    from .snapshots import snapshot
    try:
        manifest = snapshot(root)
    except Exception:
        return ""
    return digest_bytes(_json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode())


def _critic_report_from_run(root: Path, run: AgentRun, contract: CriticContract,
                            implementer_run: AgentRun, revision: str):
    """Turn a critic run into a validated report.

    The runtime owns the reviewer identity; the agent supplies the substance.
    Both are checked against the report.
    """
    if run.status != "completed":
        fallbacks = run.evidence.get("model_fallbacks", []) if run.evidence else []
        detail = ""
        if fallbacks:
            detail = " after " + "; ".join(
                f"{item.get('model')}: {str(item.get('error'))[:120]}"
                for item in fallbacks)
        return None, [f"critic run did not complete (status {run.status}){detail}"]
    # Every candidate in the answer is tried. The one that satisfies the
    # contract wins. A planted object cannot displace the real report,
    # because it does not carry the real coverage and revision.
    verified = verify_session(run.session_id, root) if run.session_id else {"verified": False}
    rejections: list[str] = []

    def _bind(report: CriticReport) -> CriticReport:
        """The runtime owns the reviewer identity, not the agent."""
        report.reviewer.session_id = run.session_id or ""
        report.reviewer.agent = run.agent or ""
        report.reviewer.model = run.model or ""
        report.reviewer.execution_mode = run.evidence.get("execution_mode", "native")
        report.reviewer.verified = bool(verified.get("verified"))
        report.reviewer.read_only_agent = bool(verified.get("read_only_agent"))
        return report

    # 1. A JSON report, if the reviewer wrote one. Every candidate is tried
    # and the LAST valid one wins, because an answer usually carries its
    # result at the end, after any prose.
    json_report: Optional[CriticReport] = None
    for candidate in extract_json_objects(run.output):
        try:
            report = CriticReport.from_dict(candidate)
        except Invalid as exc:
            rejections.append(str(exc))
            continue
        _bind(report)
        errors = validate_critic_report(
            report,
            expected_task_id=contract.task_id,
            expected_reviewed_task_id=contract.review_target,
            expected_revision=revision,
            implementer_session_id=implementer_run.session_id,
            required_checks=list(contract.required_checks or []),
        )
        if not errors:
            json_report = report
            continue
        rejections.extend(errors)

    # 2. A structured prose review. A native reviewer agent usually writes one.
    extracted = parse_critic_report_markdown(
        strip_json_objects(run.output),
        requirements=list(getattr(contract, "requirements", []) or []),
        required_checks=list(contract.required_checks or []),
        require_verdict=False)
    prose_report: Optional[CriticReport] = None
    if extracted is not None:
        extracted.task_id = contract.task_id
        extracted.reviewed_task_id = contract.review_target
        extracted.reviewed_revision = revision
        _bind(extracted)
        errors = validate_critic_report(
            extracted,
            expected_task_id=contract.task_id,
            expected_reviewed_task_id=contract.review_target,
            expected_revision=revision,
            implementer_session_id=implementer_run.session_id,
            required_checks=list(contract.required_checks or []),
            require_recommendation=False,
        )
        if not errors:
            prose_report = extracted
        else:
            rejections.extend(errors)

    if json_report is not None and extracted is not None:
        # The answer carries two reports. They may not disagree, and the
        # prose may add findings the JSON report does not carry. The findings
        # of the prose count even when the prose report as a whole is
        # incomplete: a blocking defect stated in the text is a blocking
        # defect.
        if (extracted.recommendation
                and json_report.recommendation != extracted.recommendation):
            return None, [
                "the answer carries two reports that disagree: a JSON report "
                f"recommends '{json_report.recommendation}' and the review text "
                f"recommends '{extracted.recommendation}'"]
        known = {(finding.file, finding.issue) for finding in json_report.findings}
        for finding in extracted.findings:
            if (finding.file, finding.issue) not in known:
                json_report.findings.append(finding)
                known.add((finding.file, finding.issue))
        if (json_report.recommendation == "approve"
                and any(finding.severity == "blocker"
                        for finding in json_report.findings)):
            # The review text states a blocking defect that the report does
            # not carry. An approval that contradicts the review is refused.
            return None, [
                "the review text states a blocking defect that the report does "
                "not carry"]
    if json_report is not None:
        return json_report, []
    if prose_report is not None:
        if not prose_report.recommendation:
            return None, ["the review states no verdict the core could read"]
        return prose_report, []

    if not rejections:
        rejections.append("the critic produced no report")
    return None, rejections[:12]


def pair_execution_cli(root: Path, command: str, **kwargs) -> int:
    try:
        if command != "run-pair":
            print(f"Unknown command: {command}", file=sys.stderr)
            return 1

        impl_id = kwargs["impl_task_id"]
        critic_id = kwargs.get("critic_task_id") or f"critic-{impl_id}"
        max_rounds = kwargs.get("max_rounds", 2)

        impl_contract = load_contract(root, impl_id)
        critic_contract = load_contract(root, critic_id)

        # The pair establishes the review assignment. Without this link the
        # integration report cannot attribute a reviewer to the change.
        if impl_contract.review_assignment != critic_id:
            impl_contract.review_assignment = critic_id
            save_contract(impl_contract, root)

        print(f"Running implementer: {impl_id}")
        impl_run = run_implementer(root, impl_contract)
        impl_data = _parse_agent_output(impl_run)
        # The implementer filled in its own contract. That record is the
        # result; the extracted answer is only the fallback.
        record = _read_task_record(root, impl_id)
        if record:
            impl_data = _merge_task_record(impl_data, record)

        # The revision under review is the tree the implementer just produced.
        # It is taken after the implementer wrote its files, so a report that
        # honestly names the revision it saw is accepted and a report that
        # names an older one is refused.
        revision = _current_revision(root)

        impl_contract.status = impl_data.get("status", impl_run.status)
        impl_contract.changes = impl_data.get("changes") or []
        impl_contract.findings = impl_data.get("findings") or []
        impl_contract.evidence = impl_data.get("evidence") or {}
        impl_contract.checks = impl_data.get("checks") or []
        impl_contract.risks = impl_data.get("risks") or []
        impl_contract.unresolved = impl_data.get("unresolved") or []
        impl_contract.review_notes = impl_data.get("review_notes") or ""
        impl_contract.session_id = impl_run.session_id
        impl_contract.agent = impl_run.agent
        impl_contract.model = impl_run.model
        impl_contract.execution_mode = impl_run.evidence.get("execution_mode", "native")
        save_contract(impl_contract, root)

        if impl_run.status == "unavailable":
            print("UNAVAILABLE: OpenCode runtime not reachable. "
                  "No simulated result was produced.")
            critic_contract.status = "unavailable"
            save_contract(critic_contract, root)
            return 2
        if impl_run.status != "completed":
            # A crashed or incomplete implementer run is not a delivery.
            print(f"FAILED: implementer run did not complete "
                  f"(status {impl_run.status}): {impl_run.error}")
            impl_contract.status = "failed"
            save_contract(impl_contract, root)
            critic_contract.status = "not_run"
            save_contract(critic_contract, root)
            return 3

        print(f"Running critic: {critic_id}")
        critic_run = run_critic(root, critic_contract, impl_data,
                                revision=revision,
                                implementer_session_id=impl_run.session_id or "")
        report, report_errors = _critic_report_from_run(
            root, critic_run, critic_contract, impl_run, revision)
        if report_errors:
            for reason in report_errors:
                print(f"  ! critic report rejected: {reason}")
            # The session that ran is still recorded, so a refused review
            # leaves the same kind of evidence a successful one does.
            critic_contract.status = "failed"
            critic_contract.session_id = critic_run.session_id
            critic_contract.agent = critic_run.agent
            critic_contract.model = critic_run.model
            critic_contract.execution_mode = critic_run.evidence.get("execution_mode", "native")
            critic_contract.review_notes = "; ".join(report_errors)[:1500]
            critic_evidence = dict(critic_contract.evidence or {})
            critic_evidence["model_fallbacks"] = critic_run.evidence.get(
                "model_fallbacks", [])
            critic_evidence["model_requested_profile"] = critic_run.evidence.get(
                "model_requested_profile")
            critic_contract.evidence = critic_evidence
            save_contract(critic_contract, root)
            print("FAILED: the critic report did not satisfy the review contract.")
            return 5
        critic_data = _parse_agent_output(critic_run)
        critic_data["session_id"] = critic_run.session_id
        critic_data["agent"] = critic_run.agent
        critic_data["model"] = critic_run.model
        if report is not None:
            # The validated report is the review. Its findings are what the
            # repair loop works on, whatever form the reviewer answered in.
            critic_data["findings"] = report.to_dict().get("findings") or []
            critic_data["critic_report"] = report.to_dict()

        final_critic, trail = repair_loop(
            root, impl_contract, critic_data, max_rounds, critic_contract,
            revision=revision)

        critic_contract.status = final_critic.get("status", critic_run.status)
        critic_contract.findings = final_critic.get("findings") or []
        critic_contract.evidence = final_critic.get("evidence") or {}
        critic_contract.checks = final_critic.get("checks") or []
        critic_contract.review_notes = final_critic.get("recommendation") or ""
        # The findings come from the last re-review, so the session must be
        # the one that produced them.
        final_session = final_critic.get("session_id") or critic_run.session_id
        critic_contract.session_id = final_session
        critic_contract.agent = critic_run.agent
        critic_contract.model = critic_run.model
        critic_contract.execution_mode = critic_run.evidence.get("execution_mode", "native")
        # The provider fallbacks belong in the evidence: which models were
        # tried and why each one failed.
        critic_evidence = dict(critic_contract.evidence or {})
        critic_evidence["model_fallbacks"] = critic_run.evidence.get("model_fallbacks", [])
        critic_evidence["model_requested_profile"] = critic_run.evidence.get(
            "model_requested_profile")
        critic_contract.evidence = critic_evidence
        # The stored report is the final one. A first review that a re-review
        # superseded must not stay in the artifact, and the report's reviewer
        # session must be the session the contract records.
        stored_report = final_critic.get("critic_report")
        if stored_report:
            critic_contract.critic_report = stored_report
            stored = parse_critic_report(json.dumps(stored_report))
            critic_contract.review_notes = stored.summary
            critic_contract.findings = [f.issue for f in stored.findings]
        elif report is not None:
            critic_contract.critic_report = report.to_dict()
            critic_contract.review_notes = report.summary
            critic_contract.findings = [f.issue for f in report.findings]
        save_contract(critic_contract, root)

        critic_for_evidence = critic_run
        if final_session and final_session != critic_run.session_id:
            critic_for_evidence = AgentRun(
                status=critic_run.status, session_id=final_session,
                agent=final_critic.get("agent") or critic_run.agent,
                model=final_critic.get("model") or critic_run.model,
                output="", events=[],
                evidence=dict(critic_run.evidence), error=critic_run.error)
        independence = independence_report(impl_run, critic_for_evidence, root)
        report_path = root / ".architect-dev-team" / "pair_evidence.json"
        report_path.parent.mkdir(exist_ok=True)
        # The evidence carries the final report, not the first one: a re-review
        # that superseded the first review is the review of record.
        report_path.write_text(json.dumps({
            "implementer": impl_run.to_dict(),
            "critic": critic_run.to_dict(),
            "final_critic_report": final_critic.get("critic_report"),
            "final_critic_session_id": final_session,
            "independence": independence,
            "repair_trail": trail,
        }, indent=2, ensure_ascii=False), encoding="utf-8")

        print(f"Pair execution complete. Critic findings: {len(critic_contract.findings)}")
        print(f"Independence: {independence['independence']}")
        for reason in independence["reasons"]:
            print(f"  - {reason}")
        if final_critic.get("repair_failed"):
            # A failed repair, a rejected re-review or an exhausted budget is
            # never reported as a successful pair.
            print("FAILED: the repair loop did not reach a verified result.")
            return 6
        return 0
    except Invalid as e:
        print(f"INVALID: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"INVALID: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Pair execution dispatcher")
    parser.add_argument("root", type=Path)
    parser.add_argument("command", choices=["run-pair"])
    parser.add_argument("--impl-task-id", type=str, required=True)
    parser.add_argument("--critic-task-id", type=str)
    parser.add_argument("--max-rounds", type=int, default=2)
    args = parser.parse_args()
    sys.exit(pair_execution_cli(args.root, args.command, **vars(args)))
