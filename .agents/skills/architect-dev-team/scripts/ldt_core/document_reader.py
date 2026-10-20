"""A section-aware reader for agent answers.

A native agent answers with a Markdown document: headings, paragraphs, lists
and tables. The reader understands that structure, so the extraction can take
the verdict from the verdict heading, the findings from the findings section
and the check result from the verification section, instead of matching a word
anywhere in a long answer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*\S)\s*$")

POSITIVE = re.compile(
    r"\b(?:satisfied|satisfies|compliant|compliance|passed|passes|no defects?|"
    r"no issues?|no findings?|no problems?|clean|intact|verified|ok)\b",
    re.IGNORECASE)

DEFECT_HEADING = re.compile(
    r"\b(?:defect|defects|risk|risks|finding|findings|issue|issues|problem|problems|"
    r"concern|concerns|observation|observations|gap|gaps)\b",
    re.IGNORECASE)


@dataclass
class Section:
    """One heading with its lines and its subsections."""

    heading: str = ""
    level: int = 1
    lines: list[str] = field(default_factory=list)
    children: list["Section"] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


def read_sections(body: str) -> list[Section]:
    """The heading tree of a Markdown document.

    A document without headings is one anonymous section.
    """
    root: list[Section] = []
    stack: list[Section] = []
    current: Optional[Section] = None

    for raw in (body or "").split("\n"):
        match = HEADING.match(raw.strip())
        if match:
            level = len(match.group(1))
            section = Section(heading=match.group(2), level=level)
            while stack and stack[-1].level >= level:
                stack.pop()
            if stack:
                stack[-1].children.append(section)
            else:
                root.append(section)
            stack.append(section)
            current = section
            continue
        if current is not None:
            current.lines.append(raw)
        else:
            if not root:
                root.append(Section(heading="", level=1))
            current = root[0]
            current.lines.append(raw)
    return root


def all_sections(tree: list[Section]) -> list[Section]:
    """Every section of the tree, in document order."""
    collected: list[Section] = []
    for section in tree:
        collected.append(section)
        collected.extend(all_sections(section.children))
    return collected


def all_lines(tree: list[Section]) -> list[str]:
    """Every line of the document, without the headings."""
    collected: list[str] = []
    for section in all_sections(tree):
        collected.extend(section.lines)
    return collected


def matching_sections(tree: list[Section], pattern: Any) -> list[Section]:
    """The sections whose heading matches the pattern."""
    compiled = pattern if hasattr(pattern, "search") else re.compile(pattern,
                                                                     re.IGNORECASE)
    return [section for section in all_sections(tree)
            if compiled.search(section.heading)]


PLACEHOLDER = re.compile(r"<[^>\n]{1,60}>")


def is_template(text: str) -> bool:
    """True when a line is a format template rather than a statement."""
    return bool(PLACEHOLDER.search(text or ""))


def section_text(section: Section) -> str:
    """The lines of a section and of its subsections."""
    parts = [section.text]
    for child in section.children:
        parts.append(child.heading)
        parts.append(section_text(child))
    return "\n".join(parts)

def balanced_end(text: str, start: int) -> int:
    """The index of the brace that closes the object at start, or -1."""
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
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
                return index
    return -1


def strip_json_objects(text: str) -> str:
    """The text without its JSON objects.

    The prose reader must not read a JSON document as prose. A report that
    names the wrong revision is decided by the JSON path, and the prose path
    must not rescue it.
    """
    if not text:
        return ""
    spans: list[tuple[int, int]] = []
    start = text.find("{")
    while start != -1:
        end = balanced_end(text, start)
        if end == -1:
            # An unbalanced brace does not end the search: the next object
            # may still be complete.
            start = text.find("{", start + 1)
            continue
        spans.append((start, end + 1))
        start = text.find("{", end + 1)
    if not spans:
        return text
    parts: list[str] = []
    cursor = 0
    for begin, finish in spans:
        parts.append(text[cursor:begin])
        cursor = finish
    parts.append(text[cursor:])
    return "\n".join(parts)

NEGATION = re.compile(
    r"\b(?:not|never|no|without|cannot|can't|doesn't|does not|did not|"
    r"wasn't|weren't|isn't|aren't|fail(?:ed|s)? to|neither|nor)\b",
    re.IGNORECASE)


def affirmed(text: str, pattern: str) -> bool:
    """True when the pattern occurs without a negation in front of it.

    "the unit test does not pass" is not a pass, and "no blocking defects
    found" is not a rejection. A line that repeats the answer template is
    not a statement and decides nothing.
    """
    for match in re.finditer(pattern, text or "", re.IGNORECASE):
        line_start = text.rfind("\n", 0, match.start()) + 1
        line_end = text.find("\n", match.start())
        if line_end == -1:
            line_end = len(text)
        if is_template(text[line_start:line_end]):
            continue
        window = text[max(0, match.start() - 30):match.start()]
        if not NEGATION.search(window):
            return True
    return False
