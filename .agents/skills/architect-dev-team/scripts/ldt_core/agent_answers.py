"""
Agent answer extraction.

A native agent in this runtime answers with prose and Markdown, not with a
JSON object, even when the prompt asks for one. The substance is there; the
machine-readable form is missing.

This module turns such an answer into the structured fields the workflow
needs. The result always records where it came from, so a reader can tell a
reported field from an extracted one. Nothing is invented: a field that the
answer does not state stays empty and the caller's validation refuses the
result.

Python 3.10+, stdlib only.
"""
from __future__ import annotations
import re
from typing import Any, Optional

from .document_reader import (
    all_lines, all_sections, affirmed, is_template, matching_sections,
    read_sections,
)


TASK_ID_PATTERN = re.compile(r"\b([a-z][a-z0-9]*(?:-[a-z0-9]+)*-\d+)\b")

NEGATION = re.compile(
    r"\b(?:not|never|no|without|cannot|can't|doesn't|does not|did not|"
    r"wasn't|weren't|isn't|aren't|fail(?:ed|s)? to|neither|nor)\b",
    re.IGNORECASE)


def _affirmed(text: str, pattern: str) -> bool:
    """True when the pattern occurs without a negation in front of it."""
    return affirmed(text, pattern)

def _section(text: str, *titles: str) -> list[str]:
    """The lines of the first section whose heading matches one of the titles.

    The titles are tried in the order they are given, so the most specific
    heading wins even when a broader one appears earlier in the answer.
    """
    lines = text.split("\n")
    for title in titles:
        for index, line in enumerate(lines):
            if not re.search(title, line, re.IGNORECASE):
                continue
            collected: list[str] = []
            for candidate in lines[index + 1:]:
                stripped = candidate.strip()
                if stripped.startswith("#"):
                    break
                if stripped:
                    collected.append(stripped)
            if collected:
                return collected
    return []


def _mentions(text: str, *patterns: str) -> bool:
    """True when the answer matches any of the patterns."""
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def extract_specialist_result(text: str) -> dict[str, Any]:
    """The result of a specialist that answered in prose.

    The reader takes the changed files from the changes section, the check
    results from the check section and the status from the answer's own
    words. A field the answer does not state stays empty.
    """
    result: dict[str, Any] = {
        "status": "",
        "changes": [],
        "acceptance_met": False,
        "findings": [],
        "evidence": {},
        "checks": [],
        "risks": [],
        "unresolved": [],
        "summary": "",
        "extracted_from": "markdown",
    }
    if not (text or "").strip():
        result["status"] = "failed"
        result["summary"] = "the specialist produced no output"
        return result

    tree = read_sections(text)

    # The changed files.
    for section in matching_sections(
            tree, r"\b(?:changes?|files? changed|modified|touched)\b"):
        for line in section.lines:
            for match in re.finditer(r"\b([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)\b", line):
                path = match.group(1)
                if path not in result["changes"]:
                    result["changes"].append(path)

    # The checks and their result.
    for section in matching_sections(
            tree, r"\b(?:checks?|tests? (?:run|results?)|verification)\b"):
        for line in section.lines:
            if is_template(line):
                continue
            match = re.match(
                r"^[-*|\s]*`?([A-Za-z0-9_.\-/]+)`?\s*[:|\-]\s*"
                r"(passed|failed|pass|fail|not_run|not run|skipped)", line,
                re.IGNORECASE)
            if not match:
                continue
            name = match.group(1)
            outcome = match.group(2).lower()
            outcome = ("passed" if outcome.startswith("pass")
                       else "failed" if outcome.startswith("fail")
                       else "not_run")
            result["checks"].append({"name": name, "result": outcome,
                                     "evidence": line[:300]})
            result["evidence"][name] = line[:300]
    if not result["checks"]:
        for line in all_lines(tree):
            if is_template(line):
                continue
            match = re.search(r"\b([A-Za-z0-9_.\-/]+)\b[^\n]{0,20}\b"
                              r"(passed|failed|not run)\b", line, re.IGNORECASE)
            if not match:
                continue
            name = match.group(1)
            if name in {"the", "a", "an", "tests", "test", "suite"}:
                continue
            outcome = match.group(2).lower()
            outcome = ("passed" if outcome.startswith("pass")
                       else "failed" if outcome.startswith("fail") else "not_run")
            result["checks"].append({"name": name, "result": outcome,
                                     "evidence": line[:300]})
            result["evidence"][name] = line[:300]
            break

    # The acceptance criteria. Only an affirmation counts.
    result["acceptance_met"] = (
        _affirmed(text, r"\ball acceptance criteria are met\b")
        or _affirmed(text, r"\bacceptance criteria (?:are|is) met\b")
        or _affirmed(text, r"\bmeets the acceptance criteria\b")
        or _affirmed(text, r"\bacceptance[ _]met\b")
        or _affirmed(text, r"\ball (?:the )?requirements (?:are|is) met\b"))

    # The status, from the answer's own words.
    if _affirmed(text, r"status:\s*\"?blocked\b") or _affirmed(text, r"\bblocked\b"):
        result["status"] = "blocked"
    elif _affirmed(text, r"status:\s*\"?failed\b") or \
            _affirmed(text, r"\bcould not\b") or _affirmed(text, r"\bunable to\b"):
        result["status"] = "failed"
    elif _affirmed(text, r"status:\s*\"?completed\b") or \
            _affirmed(text, r"\bcompleted\b") or _affirmed(text, r"\bdone\b") or \
            _affirmed(text, r"\bfinished\b"):
        result["status"] = "completed"
    else:
        result["status"] = "completed" if result["acceptance_met"] else "failed"

    # The summary.
    for section in matching_sections(tree, r"\b(?:summary|result|what i did|outcome)\b"):
        for line in section.lines:
            stripped = line.strip()
            if len(stripped) > 40:
                result["summary"] = stripped[:600]
                break
        if result["summary"]:
            break
    if not result["summary"]:
        for section in all_sections(tree):
            for line in section.lines:
                stripped = line.strip()
                if len(stripped) > 40 and not stripped.startswith(("|", "`", "-", "*", "=")):
                    result["summary"] = stripped[:600]
                    break
            if result["summary"]:
                break

    # The risks and the open points.
    for section in matching_sections(tree, r"\b(?:risks?|concerns?|flags?)\b"):
        for line in section.lines:
            stripped = line.strip()
            if stripped:
                result["risks"].append(stripped[:300])
    for section in matching_sections(
            tree, r"\b(?:unresolved|open (?:items|points|questions)|not (?:done|completed))\b"):
        for line in section.lines:
            stripped = line.strip()
            if stripped:
                result["unresolved"].append(stripped[:300])
    return result


def extract_lead_review(text: str,
                        task_ids: Optional[list[str]] = None) -> dict[str, Any]:
    """The decision of a Department Lead that answered in prose.

    The verdict comes from the verdict heading. The decision on a specialist
    comes from the line that names that specialist and states a decision.
    """
    review: dict[str, Any] = {
        "accepted": False,
        "decisions": [],
        "unresolved": [],
        "escalated": False,
        "summary": "",
        "extracted_from": "markdown",
    }
    if not (text or "").strip():
        return review

    tree = read_sections(text)
    known = [str(item) for item in (task_ids or [])]

    # The verdict.
    verdict_line = ""
    for section in all_sections(tree):
        if not re.search(r"\b(?:verdict|outcome|recommendation)\b", section.heading,
                         re.IGNORECASE):
            continue
        verdict_line = section.heading
        break
    if not verdict_line:
        for line in all_lines(tree):
            if re.search(r"\b(?:recommended|verdict|outcome)\b", line, re.IGNORECASE):
                verdict_line = line
                break
    verdict = _verdict_decision(verdict_line)

    # A specialist the core does not know. The lead must not decide about a
    # task outside the agreed roster, and the core does not guess which
    # roster task it meant.
    named_outside = False
    for line in all_lines(tree):
        for match in TASK_ID_PATTERN.finditer(line):
            name = match.group(1)
            if name not in known:
                named_outside = True
                break

    # The decision on each specialist. The decision section decides; only
    # when the lead has none does the narrative count.
    decision_lines: list[str] = []
    for pattern in (r"\bdecisions?\b", r"\b(?:assessment|per specialist|review of)\b"):
        for section in matching_sections(tree, pattern):
            decision_lines.extend(section.lines)
        if decision_lines:
            break
    if not decision_lines:
        decision_lines = all_lines(tree)

    for line in decision_lines:
        task_id = ""
        position = -1
        for candidate in known:
            if candidate and candidate in line:
                task_id = candidate
                position = line.find(candidate)
                break
        if not task_id and not known:
            # Without an agreed roster the task id is recognised in the line.
            match = TASK_ID_PATTERN.search(line)
            if match:
                task_id = match.group(1)
                position = match.start()
        if not task_id:
            continue
        # The decision is read from the neighbourhood of the specialist. A
        # word far away in a long narrative belongs to something else.
        decision = _verdict_decision(line[max(0, position):position + 160])
        if not decision:
            continue
        rejected = decision == "reject"
        review["decisions"].append({
            "task_id": task_id,
            "decision": "reject" if rejected else "accept",
            "reason": line[:300],
            "correction": {"goal": "" if not rejected else line[:200],
                           "checks": []},
        })
    # One decision per specialist.
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for decision in review["decisions"]:
        if decision["task_id"] in seen:
            continue
        seen.add(decision["task_id"])
        unique.append(decision)
    review["decisions"] = unique

    if not verdict and review["decisions"]:
        # The lead has no verdict heading. Its decisions are the verdict.
        verdict = ("reject" if any(decision["decision"] == "reject"
                                   for decision in review["decisions"]) else "approve")
    review["accepted"] = verdict == "approve" and not any(
        decision["decision"] == "reject" for decision in review["decisions"])
    if named_outside and not review["decisions"]:
        # The lead decided about a task outside the agreed roster. The core
        # cannot map that verdict onto the roster and does not guess.
        review["accepted"] = False

    if (not review["decisions"] and review["accepted"] and len(known) == 1
            and not named_outside):
        # The lead accepted the work without naming a specialist, and there is
        # exactly one specialist it could mean. The verdict is the decision
        # then. With more than one specialist, or with a specialist the core
        # does not know, the core does not guess.
        review["decisions"].append({
            "task_id": known[0],
            "decision": "accept",
            "reason": verdict_line[:300],
            "correction": {"goal": "", "checks": []},
        })

    if _affirmed(text, r"\bescalat") or _affirmed(text, r"\bblocking\b") or \
            _affirmed(text, r"\bcannot be completed\b"):
        review["escalated"] = True

    for section in matching_sections(
            tree, r"\b(?:unresolved|open (?:items|points|questions)|flagged|carry over)\b"):
        for line in section.lines:
            stripped = line.strip()
            if stripped:
                review["unresolved"].append(stripped[:300])

    for section in matching_sections(tree, r"\b(?:summary|verdict|conclusion)\b"):
        for line in section.lines:
            stripped = line.strip()
            if len(stripped) > 40:
                review["summary"] = stripped[:600]
                break
        if review["summary"]:
            break
    if not review["summary"] and verdict_line:
        review["summary"] = verdict_line.strip()[:600]
    return review


def _verdict_decision(text: str) -> str:
    """The decision a line states: approve or reject.

    A decision word in a denial decides nothing: "no blocking defects found"
    is not a rejection.
    """
    if not text:
        return ""
    if affirmed(text, r"\breject(?:ed|ing)?\b|"
                      r"\b(?:i|we|the lead|the reviewer|the critic)\s+rejects\b") or \
            affirmed(text, r"\bneeds? (?:work|correction)\b") or \
            affirmed(text, r"\bdoes not pass\b") or \
            affirmed(text, r"\bnot usable\b") or \
            affirmed(text, r"\bfailed\b") or \
            affirmed(text, r"\bblock(?:ed|ing)?\b"):
        return "reject"
    if affirmed(text, r"\baccept(?:ed|s)?\b") or \
            affirmed(text, r"\bapprov(?:ed|al)\b") or \
            affirmed(text, r"\bcomplet(?:ed|ion)\b") or \
            affirmed(text, r"\bpass(?:ed|es)?\b") or \
            affirmed(text, r"\bpass\b") or \
            affirmed(text, r"\bsatisf(?:ied|ies)\b") or \
            affirmed(text, r"\bno correction round\b"):
        return "approve"
    return ""
