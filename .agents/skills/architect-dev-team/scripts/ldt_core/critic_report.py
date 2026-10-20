"""
CriticReport: a validated, machine-verifiable review contract.

A review does not pass because a session existed. The report must carry
execution evidence, coverage, findings, confidence and a recommendation, and
it must be bound to the revision it actually reviewed.

Python 3.10+, stdlib only.
"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from .document_reader import (
    BULLET, DEFECT_HEADING, POSITIVE, Section, affirmed, all_lines, all_sections,
    is_template, matching_sections, read_sections, section_text,
)
from .common import Invalid, relative


def extract_json_objects(text: str) -> list[dict[str, Any]]:
    """Every balanced JSON object in an answer, in order of appearance.

    The agent may wrap the object in a code fence or add a short remark. All
    candidates are returned so the caller can pick the one that satisfies
    the contract; an object planted earlier in the answer does not win by
    position alone.
    """
    candidate = (text or "").strip()
    if not candidate:
        return []
    found: list[dict[str, Any]] = []
    start = candidate.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escaped = False
        end = -1
        for index in range(start, len(candidate)):
            char = candidate[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = index
                    break
        if end == -1:
            break
        block = candidate[start:end + 1]
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            found.append(data)
        start = candidate.find("{", end + 1)
    return found


def extract_json_objects_deep(text: str) -> list[dict[str, Any]]:
    """Every balanced JSON object in an answer, including nested ones."""
    found: list[dict[str, Any]] = []
    for candidate in extract_json_objects(text):
        found.append(candidate)
        for value in candidate.values():
            if isinstance(value, dict):
                found.append(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        found.append(item)
    return found


def extract_json_object(text: str, required_keys: Optional[list[str]] = None,
                        required_any: Optional[list[str]] = None
                        ) -> Optional[dict[str, Any]]:
    """Find a JSON object in an answer.

    `required_keys` demands all of them, `required_any` demands at least one.
    The first candidate that satisfies the requirement wins, so an object
    planted earlier in the answer does not win by position alone.
    """
    candidates = extract_json_objects(text)
    if not candidates:
        return None
    if required_keys:
        matching = [c for c in candidates if all(key in c for key in required_keys)]
        if not matching:
            return None
        # A tie keeps the last candidate: an answer usually carries its
        # result at the end, after any prose or a planted object.
        best = max(sum(1 for key in required_keys if key in c) for c in matching)
        return [c for c in matching
                if sum(1 for key in required_keys if key in c) == best][-1]
    if required_any:
        matching = [c for c in candidates if any(key in c for key in required_any)]
        if not matching:
            return None
        # The candidate that matches the most of the expected keys wins, so a
        # planted object with fewer keys cannot displace the real answer.
        best = max(sum(1 for key in required_any if key in c) for c in matching)
        return [c for c in matching
                if sum(1 for key in required_any if key in c) == best][-1]
    return candidates[0]


SEVERITIES = ("blocker", "major", "minor", "info")
RECOMMENDATIONS = ("approve", "approve_with_findings", "reject")
CONFIDENCE = ("high", "medium", "low")
MAX_SUMMARY_CHARS = 2000


@dataclass
class Reviewer:
    """Who performed the review, with the evidence that proves it."""
    session_id: str = ""
    agent: str = ""
    model: str = ""
    execution_mode: str = ""
    verified: bool = False
    read_only_agent: bool = False

    @staticmethod
    def from_dict(value: Any) -> "Reviewer":
        if not isinstance(value, dict):
            raise Invalid("reviewer must be an object")
        return Reviewer(
            session_id=str(value.get("session_id", "") or ""),
            agent=str(value.get("agent", "") or ""),
            model=str(value.get("model", "") or ""),
            execution_mode=str(value.get("execution_mode", "") or ""),
            verified=bool(value.get("verified", False)),
            read_only_agent=bool(value.get("read_only_agent", False)),
        )


@dataclass
class Coverage:
    """What the reviewer actually looked at."""
    requirements_checked: list[str] = field(default_factory=list)
    files_inspected: list[str] = field(default_factory=list)
    interfaces_checked: list[str] = field(default_factory=list)
    evidence_references: list[str] = field(default_factory=list)
    checks_run: list[dict[str, str]] = field(default_factory=list)
    unverified_areas: list[str] = field(default_factory=list)

    @staticmethod
    def from_dict(value: Any) -> "Coverage":
        if not isinstance(value, dict):
            raise Invalid("coverage must be an object")
        def strings(key: str) -> list[str]:
            raw = value.get(key, [])
            if not isinstance(raw, list):
                raise Invalid(f"coverage.{key} must be a list")
            return [str(item) for item in raw]
        checks = value.get("checks_run", [])
        if not isinstance(checks, list):
            raise Invalid("coverage.checks_run must be a list")
        return Coverage(
            requirements_checked=strings("requirements_checked"),
            files_inspected=strings("files_inspected"),
            interfaces_checked=strings("interfaces_checked"),
            evidence_references=strings("evidence_references"),
            checks_run=[c for c in checks if isinstance(c, dict)],
            unverified_areas=strings("unverified_areas"),
        )


@dataclass
class Finding:
    severity: str = ""
    file: str = ""
    line: Any = None
    issue: str = ""
    reproduction: str = ""
    reference: str = ""

    @staticmethod
    def from_dict(value: Any) -> "Finding":
        if not isinstance(value, dict):
            raise Invalid("finding must be an object")
        return Finding(
            severity=str(value.get("severity", "") or ""),
            file=str(value.get("file", "") or ""),
            line=value.get("line"),
            issue=str(value.get("issue", "") or ""),
            reproduction=str(value.get("reproduction", "") or ""),
            reference=str(value.get("reference", "") or ""),
        )


@dataclass
class CriticReport:
    """The machine-verifiable result of one independent review."""
    task_id: str = ""
    reviewed_task_id: str = ""
    reviewed_revision: str = ""
    reviewer: Reviewer = field(default_factory=Reviewer)
    coverage: Coverage = field(default_factory=Coverage)
    findings: list[Finding] = field(default_factory=list)
    verified_non_findings: list[str] = field(default_factory=list)
    confidence: str = ""
    limitations: list[str] = field(default_factory=list)
    recommendation: str = ""
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @staticmethod
    def from_dict(value: Any) -> "CriticReport":
        if not isinstance(value, dict):
            raise Invalid("critic report must be a JSON object")
        findings = value.get("findings", [])
        if not isinstance(findings, list):
            raise Invalid("findings must be a list")
        non_findings = value.get("verified_non_findings", [])
        if not isinstance(non_findings, list):
            raise Invalid("verified_non_findings must be a list")
        limitations = value.get("limitations", [])
        if not isinstance(limitations, list):
            raise Invalid("limitations must be a list")
        return CriticReport(
            task_id=str(value.get("task_id", "") or ""),
            reviewed_task_id=str(value.get("reviewed_task_id", "") or ""),
            reviewed_revision=str(value.get("reviewed_revision", "") or ""),
            reviewer=Reviewer.from_dict(value.get("reviewer", {})),
            coverage=Coverage.from_dict(value.get("coverage", {})),
            findings=[Finding.from_dict(f) for f in findings],
            verified_non_findings=[str(f) for f in non_findings],
            confidence=str(value.get("confidence", "") or ""),
            limitations=[str(item) for item in limitations],
            recommendation=str(value.get("recommendation", "") or ""),
            summary=str(value.get("summary", "") or ""),
        )


def parse_critic_report(text: str) -> CriticReport:
    """Parse the reviewer's JSON output into a report.

    The object may be wrapped in a code fence or preceded by a short remark.
    Only a complete, balanced JSON object is accepted, and the content is
    validated strictly afterwards, so a lenient extraction never means a
    lenient verdict.
    """
    if not (text or "").strip():
        raise Invalid("critic produced no output")
    data = extract_json_object(text, required_keys=[
        "task_id", "reviewed_task_id", "reviewed_revision",
        "reviewer", "coverage", "findings", "confidence", "recommendation", "summary"])
    if data is None:
        raise Invalid("critic report contains no complete JSON object with the "
                      "required fields")
    return CriticReport.from_dict(data)


def validate_critic_report(
    report: CriticReport,
    *,
    expected_task_id: str,
    expected_reviewed_task_id: str,
    expected_revision: str,
    implementer_session_id: Optional[str] = None,
    required_checks: Optional[list[str]] = None,
    require_recommendation: bool = True,
) -> list[str]:
    """Check a report against the facts the runtime knows.

    Returns the list of rejection reasons. An empty list means the report
    satisfies the contract.
    """
    errors: list[str] = []

    # --- identity and revision binding ---------------------------------
    if report.task_id != expected_task_id:
        errors.append(f"report task_id '{report.task_id}' does not match the critic task "
                      f"'{expected_task_id}'")
    if report.reviewed_task_id != expected_reviewed_task_id:
        errors.append(f"report reviewed_task_id '{report.reviewed_task_id}' does not match "
                      f"the reviewed task '{expected_reviewed_task_id}'")
    if not report.reviewed_revision:
        errors.append("report does not name the revision it reviewed")
    elif not expected_revision:
        # The core does not know which revision it is looking at. A report
        # that claims a revision cannot be checked, so it is not accepted.
        errors.append("the revision under review is unknown; the report cannot "
                      "be bound to it")
    elif report.reviewed_revision != expected_revision:
        errors.append(f"report is bound to revision {report.reviewed_revision} but the "
                      f"current revision is {expected_revision}")

    # --- execution evidence --------------------------------------------
    if not report.reviewer.session_id:
        errors.append("report carries no reviewer session id")
    if implementer_session_id and report.reviewer.session_id == implementer_session_id:
        errors.append("reviewer session is the implementer session")
    if report.reviewer.execution_mode != "native":
        errors.append(f"reviewer execution mode is '{report.reviewer.execution_mode}', "
                      "not a native agent run")
    if not report.reviewer.verified:
        errors.append("reviewer session is not verified in the runtime")
    if not report.reviewer.read_only_agent:
        errors.append("reviewer agent is not read-only, so the review is not independent "
                      "of production code")
    if not report.reviewer.agent:
        errors.append("report does not name the reviewing agent")
    if not report.reviewer.model:
        errors.append("report does not name the reviewing model")

    # --- coverage -------------------------------------------------------
    if not report.coverage.requirements_checked:
        errors.append("report names no checked requirements")
    if not report.coverage.files_inspected:
        errors.append("report names no inspected files")
    for path in report.coverage.files_inspected:
        try:
            relative(path)
        except Invalid as exc:
            errors.append(f"invalid file reference '{path}': {exc}")
    ran: dict[str, dict[str, Any]] = {}
    for check in report.coverage.checks_run:
        name = str(check.get("name", "") or "")
        result = str(check.get("result", "") or "")
        evidence = str(check.get("evidence", "") or "")
        if not name:
            errors.append("a coverage check has no name")
        if not result:
            errors.append(f"coverage check '{name}' has no result")
        if not evidence:
            errors.append(f"coverage check '{name}' claims a result without evidence")
        ran[name] = check

    # Every required check of the contract must be covered, with a real
    # result. A check that was not run is reported as such and blocks the
    # acceptance of the review.
    for name in (required_checks or []):
        check = ran.get(name)
        if check is None:
            errors.append(f"the report does not cover the required check '{name}'")
            continue
        result = str(check.get("result", "") or "")
        if result not in ("passed", "failed", "not_run"):
            errors.append(f"required check '{name}' has an invalid result '{result}'")
        if result == "not_run" and not str(check.get("evidence", "") or "").strip():
            errors.append(f"required check '{name}' was not run and does not say why")

    # Evidence references must stay inside the project.
    for reference in report.coverage.evidence_references:
        candidate = reference.split(":", 1)[0].strip()
        if not candidate or candidate.startswith("python ") or candidate.startswith("$"):
            continue
        try:
            relative(candidate)
        except Invalid:
            errors.append(f"invalid evidence reference '{reference}'")

    # A report that claims a test ran must show the check.
    for reference in report.coverage.evidence_references:
        lowered = reference.lower()
        if "pytest" in lowered or "unittest" in lowered or "passed" in lowered:
            if not report.coverage.checks_run:
                errors.append("the report claims a test result without any check")

    # --- findings --------------------------------------------------------
    for finding in report.findings:
        if finding.severity not in SEVERITIES:
            errors.append(f"finding severity '{finding.severity}' is invalid")
        if not finding.file:
            errors.append("finding has no file reference")
        else:
            try:
                relative(finding.file)
            except Invalid as exc:
                errors.append(f"invalid finding file reference '{finding.file}': {exc}")
        if not finding.issue:
            errors.append("finding has no issue description")
        if finding.severity in ("blocker", "major") and not finding.reproduction:
            errors.append(f"finding '{finding.issue[:60]}' has no reproduction")
    if not report.findings and not report.verified_non_findings:
        errors.append("report states neither a finding nor a verified non-finding")

    # --- blockers may not be approved away ------------------------------
    blocking = [f for f in report.findings if f.severity == "blocker"]
    if blocking and report.recommendation == "approve":
        errors.append(f"report recommends approval although {len(blocking)} blocking "
                      "finding(s) are unresolved")
    if blocking and report.recommendation not in ("reject", "approve_with_findings"):
        errors.append("report with blocking findings needs a rejecting recommendation")

    # --- confidence and recommendation ----------------------------------
    if report.confidence not in CONFIDENCE:
        errors.append(f"confidence '{report.confidence}' is invalid")
    if require_recommendation and report.recommendation not in RECOMMENDATIONS:
        errors.append(f"recommendation '{report.recommendation}' is invalid")
    if not report.summary:
        errors.append("report has no human readable summary")
    elif len(report.summary) > MAX_SUMMARY_CHARS:
        errors.append("report summary is too long to be a concise handover")

    return errors


def _keywords(requirement: str) -> list[str]:
    words = []
    for raw in requirement.replace("`", " ").replace("_", " ").split():
        word = "".join(ch for ch in raw.lower() if ch.isalnum())
        if len(word) > 3 and word not in STOP_WORDS:
            words.append(word)
    return words


def _requirement_covered(requirement: str, body_lower: str) -> bool:
    """True when the review mentions the meaningful words of the requirement."""
    words = _keywords(requirement)
    if not words:
        return False
    found = [word for word in words if word in body_lower]
    return len(found) >= max(1, len(words) - 1)


def _names_another_check(line: str, name: str, all_names: list[str]) -> bool:
    """True when a line names a check other than the one in question.

    The names of every check the document mentions are compared, not only
    the ones the contract requires: a count that belongs to a check the
    contract does not know is still a count of another check.
    """
    lowered = line.lower()
    for other in all_names:
        if other == name:
            continue
        if _check_named(other, lowered):
            return True
    for other in _check_names_in_line(line):
        if other != name:
            return True
    return False


CHECK_NAME_PATTERN = re.compile(
    r"\b([A-Za-z0-9_]+(?:[-.][A-Za-z0-9_]+)*-(?:tests?|checks?|lint|typecheck|build))\b",
    re.IGNORECASE)


def _check_names_in_line(line: str) -> list[str]:
    """The check names a line names."""
    names: list[str] = []
    for match in CHECK_NAME_PATTERN.finditer(line):
        value = match.group(1)
        if value not in names:
            names.append(value)
    return names

def _states_a_count(line: str) -> bool:
    """True when a line states how many tests passed or failed."""
    return bool(re.search(r"\b\d+\s+(?:passed|failed|failures?|errors?|warnings?)\b",
                          line, re.IGNORECASE))


def _stated_check_result(line: str) -> str:
    """The result a reviewer stated for a check, read from whole words.

    The extraction must never invent a passing result. A line that names the
    check but states no outcome stays `not_run`, and a denied failure is a
    pass rather than a failure.
    """
    lowered = line.lower()
    # A check that did not run is not a pass, even when the line denies a
    # failure: "not run, no failures to report".
    if re.search(r"\bnot[_ ]run\b|\bnot executed\b|\bskipped\b|"
                 r"\bwas not run\b|\bwere not run\b", lowered):
        return "not_run"
    # A denied failure is a pass: "10 passed, no failures".
    if re.search(r"\b(?:no|zero|0)\b[^.\n]{0,24}\bfail(?:ure|ures|ed|s)?\b", lowered):
        return "passed"
    if re.search(r"\bfail(?:ure|ures|ed|s)?\b", lowered):
        return "failed"
    if re.search(r"\bpassed\b|\bpasses\b", lowered):
        return "passed"
    if re.search(r"\bok\b", lowered) and _states_a_count(line):
        return "passed"
    return "not_run"

def _check_named(name: str, body_lower: str) -> bool:
    """True when the review names the check, in a tolerant spelling."""
    variants = {
        name.lower(),
        name.lower().replace("-", "_"),
        name.lower().replace("-", " "),
        name.lower().replace("_", " "),
    }
    return any(variant and variant in body_lower for variant in variants)

STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "are", "was",
    "not", "but", "has", "have", "its", "their", "there", "than", "then",
    "when", "which", "will", "would", "could", "should", "shall", "must",
    "each", "every", "any", "all", "can", "may", "does", "done", "such",
}

SEVERITY_PATTERN = re.compile(
    r"\b(blocker|major|minor|info)\b", re.IGNORECASE)
FILE_PATTERN = re.compile(
    r"\b([A-Za-z0-9_./-]+\.(?:py|js|ts|tsx|jsx|md|json|txt|ya?ml|toml|rs|go|java|rb|c|h|cpp|cs|php|swift|kt|sql|sh))\b")
CONFIDENCE_PATTERN = re.compile(
    r"\bconfidence\b[^\n]{0,40}?\b(high|medium|low)\b", re.IGNORECASE)
VERDICT_PATTERN = re.compile(
    r"\bverdict\b[^\n]{0,120}", re.IGNORECASE)


def _mentions_severity(body: str) -> bool:
    """True when the reviewer named a severity somewhere in the answer."""
    for line in body.split("\n"):
        if not SEVERITY_PATTERN.search(line):
            continue
        if _denies_defects(line):
            continue
        return True
    return False


def _denies_defects(body: str) -> bool:
    """True when the answer states that there is no defect."""
    return bool(re.search(
        r"\b(?:no|without|zero)\b[^.\n]{0,30}\b(?:blocker|blockers|major|majors|"
        r"minor|minors|defect|defects|finding|findings|issue|issues)\b",
        body, re.IGNORECASE))

def parse_critic_report_markdown(
    text: str,
    requirements: Optional[list[str]] = None,
    required_checks: Optional[list[str]] = None,
    require_verdict: bool = True,
) -> Optional[CriticReport]:
    """Extract a critic report from a prose or Markdown review.

    The contract is the authority: the report lists exactly the requirements
    that were agreed and the checks that were agreed. The reviewer's own
    document decides whether a check passed, which findings it reported and
    what it recommends.

    The reader understands the document structure. The verdict comes from the
    verdict heading, the findings from the findings section and the check
    result from the verification section. A review the core cannot read is
    refused, never accepted as clean.
    """
    if not (text or "").strip():
        return None
    body = text
    lowered = body.lower()
    tree = read_sections(body)

    # --- the requirements the reviewer says it checked ------------------
    covered: list[str] = []
    for requirement in (requirements or []):
        if _requirement_covered(requirement, lowered):
            covered.append(requirement)

    # --- the files the reviewer names -----------------------------------
    files: list[str] = []
    for match in FILE_PATTERN.finditer(body):
        value = match.group(1)
        if value not in files:
            files.append(value)

    # --- the checks and their results -----------------------------------
    checks: list[dict[str, str]] = []
    # The sections about the check results. A requirements verification is
    # not a check result, and its rows must not be read as one.
    check_sections = matching_sections(
        tree, r"\b(?:checks?|tests?|test results?|verification results?|results?)\b")
    check_text = "\n".join(section_text(section) for section in check_sections)
    for name in (required_checks or []):
        result = "not_run"
        evidence = ""
        for line in all_lines(tree):
            if is_template(line):
                continue
            if not _check_named(name, line.lower()):
                continue
            stated = _stated_check_result(line)
            if stated != "not_run":
                result = stated
                evidence = line.strip()[:300]
                break
        if result == "not_run" and check_text:
            for line in check_text.split("\n"):
                if is_template(line):
                    continue
                # A line that names another check, or a requirement row, is
                # not the result of this check.
                if not _check_named(name, line.lower()) and not _states_a_count(line):
                    continue
                if _names_another_check(line, name, required_checks or []):
                    continue
                stated = _stated_check_result(line)
                if stated != "not_run":
                    result = stated
                    evidence = line.strip()[:300]
                    break
        checks.append({"name": name, "result": result, "evidence": evidence})

    # --- the findings ----------------------------------------------------
    findings: list[Finding] = []
    for section in matching_sections(tree, DEFECT_HEADING):
        for item in _finding_items(section):
            severity = _stated_severity(item) or _severity_of(section.heading)
            file_match = FILE_PATTERN.search(item)
            findings.append(Finding(
                severity=severity,
                file=file_match.group(1) if file_match else "",
                line=None,
                issue=item[:400],
                reproduction=item[:400],
                reference=section.heading[:200],
            ))

    if not findings and _mentions_severity(body):
        # The reviewer named a severity the core could not read out. That is
        # a remark the core does not understand, and a review it does not
        # understand is not a clean review. A denial elsewhere in the answer
        # does not excuse a defect the core could not read.
        return None

    # --- the verdict -----------------------------------------------------
    verdict_line = _verdict_line(tree)
    verdict_word = _decision_word(verdict_line) if verdict_line else ""
    if verdict_word == "reject":
        recommendation = "reject"
    elif verdict_word == "approve_with_findings":
        recommendation = "approve_with_findings"
    elif verdict_word == "approve":
        recommendation = "approve_with_findings" if findings else "approve"
    elif require_verdict:
        # The reviewer stated no verdict the core could read.
        return None
    else:
        recommendation = ""

    if _denies_defects(verdict_line) and any(
            finding.severity == "blocker" for finding in findings):
        # The verdict denies a defect and the report states a blocking one.
        # A review that contradicts itself is refused.
        return None

    confidence = "medium"
    match = CONFIDENCE_PATTERN.search(body)
    if match:
        confidence = match.group(1).lower()
    elif recommendation == "approve":
        confidence = "high"

    summary = ""
    for section in matching_sections(tree, r"\b(?:summary|verdict|conclusion|outcome)\b"):
        for line in section.lines:
            stripped = line.strip()
            if len(stripped) > 40:
                summary = stripped[:600]
                break
        if summary:
            break
    if not summary and verdict_line:
        summary = verdict_line.strip()[:600]
    if not summary and not findings:
        return None
    if not summary:
        summary = ("The reviewer stated no verdict the core could read; only "
                   "the findings were extracted.")

    unverified: list[str] = []
    match = re.search(r"\b(?:not|wasn't|did not) (?:verif|check|test)(?:ied)?\b[^\n]{0,160}",
                      body, re.IGNORECASE)
    if match:
        unverified.append(match.group(0).strip()[:200])

    if not findings and recommendation == "reject":
        # The reviewer rejected the work but the core could not read the
        # defect. A refusal is not a clean review, and the core does not
        # invent the defect either. The review is refused.
        return None

    verified_non_findings: list[str] = []
    if not findings:
        verified_non_findings.append(
            "the reviewer reported no defect and named the evidence it checked")

    report = CriticReport(
        task_id="",
        reviewed_task_id="",
        reviewed_revision="",
        reviewer=Reviewer(),
        coverage=Coverage(
            requirements_checked=covered,
            files_inspected=files,
            interfaces_checked=[],
            evidence_references=[],
            checks_run=checks,
            unverified_areas=unverified,
        ),
        findings=findings,
        verified_non_findings=verified_non_findings,
        confidence=confidence,
        limitations=[],
        recommendation=recommendation,
        summary=summary,
    )
    return report


def _denies_defects(body: str) -> bool:
    """True when the answer states that there is no defect."""
    return bool(re.search(
        r"\b(?:no|without|zero)\b[^.\n]{0,30}\b(?:blocker|blockers|major|majors|"
        r"minor|minors|defect|defects|finding|findings|issue|issues)\b",
        body, re.IGNORECASE))

def _finding_items(section: Section) -> list[str]:
    """The findings of a findings section.

    A subsection that is a findings section itself is descended into; a
    subsection that reports a satisfied criterion is not a finding.
    """
    items: list[str] = []
    for child in section.children:
        if DEFECT_HEADING.search(child.heading):
            items.extend(_finding_items(child))
            continue
        if POSITIVE.search(child.heading):
            continue
        items.append(child.heading)
    for line in section.lines:
        match = BULLET.match(line)
        if not match:
            continue
        text = match.group(1).strip()
        if not text or POSITIVE.search(text):
            continue
        items.append(text)
    if not items and not section.children:
        for line in section.lines:
            stripped = line.strip()
            if len(stripped) > 30:
                items.append(stripped)
                break
    return items


def _stated_severity(text: str) -> str:
    """The severity a text states, if it states one."""
    match = SEVERITY_PATTERN.search(text)
    if not match:
        return ""
    severity = match.group(1).lower()
    return severity if severity in SEVERITIES else ""


def _severity_of(text: str) -> str:
    """The severity a section gives its findings.

    A section that names defects gives its findings the severity `major`, a
    section that names risks gives them `info`: a risk is an observation the
    reviewer defers, a defect is a finding.
    """
    if re.search(r"\bdefects?\b", text, re.IGNORECASE):
        return "major"
    if re.search(r"\brisks?\b|\bobservations?\b|\bnotes?\b", text, re.IGNORECASE):
        return "info"
    return "info"


def _verdict_line(tree: list[Section]) -> str:
    """The line that carries the verdict."""
    for section in all_sections(tree):
        if not re.search(r"\b(?:verdict|outcome|recommendation)\b", section.heading,
                         re.IGNORECASE):
            continue
        if _decision_word(section.heading):
            return section.heading
        for candidate in section.lines:
            if _decision_word(candidate):
                return candidate
    for line in all_lines(tree):
        if not re.search(r"\b(?:recommended|verdict|outcome|recommendation)\b", line,
                         re.IGNORECASE):
            continue
        if _decision_word(line):
            return line
    return ""


def _decision_word(text: str) -> str:
    """The decision a line states: approve, approve_with_findings or reject.

    A decision word in a denial decides nothing: "no blocking defects found"
    is not a rejection.
    """
    if not text:
        return ""
    lowered = text.lower()
    if "approve_with_findings" in lowered or "approve with findings" in lowered:
        return "approve_with_findings"
    if affirmed(text, r"\breject(?:ed|ing)?\b|"
            r"\b(?:i|we|the lead|the reviewer|the critic)\s+rejects\b") or \
            affirmed(text, r"\bblock(?:ed|ing)?\b") or \
            affirmed(text, r"\bfail(?:ed|ure)?\b"):
        return "reject"
    if affirmed(text, r"\baccept(?:ed|s)?\b") or \
            affirmed(text, r"\bapprov(?:ed|al)\b") or \
            affirmed(text, r"\bcomplet(?:ed|ion)\b") or \
            affirmed(text, r"\bpass(?:ed|es)?\b") or \
            affirmed(text, r"\bpass\b") or \
            affirmed(text, r"\bsatisf(?:ied|ies)\b"):
        return "approve"
    return ""


def report_prompt(
    task_id: str,
    reviewed_task_id: str,
    revision: str,
    requirements: list[str],
    files: list[str],
    checks: list[str],
    reviewer_session_id: str,
    reviewer_agent: str,
    reviewer_model: str,
    implementation: str = "",
) -> str:
    """The prompt that asks a reviewer for a conforming report.

    The assignment comes first and is complete. A reviewer agent must not have
    to ask for the details, and it must not stop at a question.
    """
    return f"""# Review assignment

You are the Independent Critic. You review the work of another agent and
report what you find. You are read-only: you read the project, run read-only
commands, and you report. You never change a file.

The information below is complete. Do not ask for more. Do not wait for a
reply. Perform the review now and report the result.

## What is under review

Task: {reviewed_task_id}
Contract of the task under review:
{implementation[:8000]}

## Requirements you must check

{chr(10).join(f"- {r}" for r in requirements) or "- (none recorded)"}

## Files in scope

{chr(10).join(f"- {f}" for f in files) or "- (the files the task under review changed)"}

## Checks you must run and report

{chr(10).join(f"- {c}" for c in checks) or "- (none recorded)"}

## How to work

1. Read the files in scope and any test file that covers them.
2. Run the checks above and record the real result of each one, under the
   check name exactly as it is listed above.
3. Judge every requirement against the code, with a file and line reference.
4. Report every defect you find, with a severity, a location and a reproduction.
5. If you find nothing wrong, say so and name what you verified.
6. Name the areas you could not verify. Do not claim more than you checked.

## Your answer

Reply with one JSON object and nothing else. No prose before it, no prose
after it, no code fence. It has this exact shape:

{{
  "task_id": "{task_id}",
  "reviewed_task_id": "{reviewed_task_id}",
  "reviewed_revision": "{revision}",
  "reviewer": {{
    "session_id": "(your own session id)",
    "agent": "(the agent you run under)",
    "model": "(the model you run with)",
    "execution_mode": "native",
    "verified": true,
    "read_only_agent": true
  }},
  "coverage": {{
    "requirements_checked": [<one entry per requirement you actually checked>],
    "files_inspected": [<one entry per file you actually read>],
    "interfaces_checked": [<one entry per interface you checked>],
    "evidence_references": [<file:line or command references>],
    "checks_run": [{{"name": "<check name>", "result": "<passed|failed|not_run>",
                     "evidence": "<the actual output>"}}],
    "unverified_areas": [<what you did NOT verify>]
  }},
  "findings": [
    {{"severity": "<blocker|major|minor|info>", "file": "<path>", "line": <line or null>,
      "issue": "<what is wrong>", "reproduction": "<how to observe it>",
      "reference": "<requirement or spec reference>"}}
  ],
  "verified_non_findings": [<what you checked and found correct>],
  "confidence": "<high|medium|low>",
  "limitations": [<what limits your verdict>],
  "recommendation": "<approve|approve_with_findings|reject>",
  "summary": "<two to four sentences for the Department Lead>"
}}

Rules:
- Only list files you actually read and requirements you actually checked.
- A check you did not run has the result "not_run" and must say why.
- A blocking finding requires the recommendation "reject" or
  "approve_with_findings", never "approve".
- If you found nothing wrong, list what you verified in
  "verified_non_findings" and set the confidence honestly.
- Do not modify any file. If a test is missing, describe it instead of writing it.
"""
