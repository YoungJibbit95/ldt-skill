"""Existing skill-package metadata and contained-link checks."""
from pathlib import Path
import re
from urllib.parse import unquote, urlparse

from .common import require, local_file, read_json
from .registry import registry


def package(root):
    root = Path(root).resolve(strict=True)
    required = ["SKILL.md", "agents/openai.yaml", "registry/skills.json", "assets/state.template.json",
                "assets/architecture.template.md", "scripts/validate.py"]
    required += [f"scripts/ldt_core/{name}.py" for name in
                 ("__init__", "common", "snapshots", "approvals", "state", "registry", "package")]
    required += [f"references/{name}.md" for name in ("architecture", "delegation", "approvals", "delivery", "external-skills", "project-memory", "evaluation")]
    for value in required:
        local_file(root, value)
    entry = (root / "SKILL.md").read_text(encoding="utf-8")
    require(entry.startswith("---\n"), "missing YAML frontmatter")
    parts = entry.split("---", 2)
    require(len(parts) == 3, "unterminated YAML frontmatter")
    for key in ("name", "description"):
        match = re.search(rf"^{key}:\s*(.+)$", parts[1], re.MULTILINE)
        require(match is not None and match.group(1).strip() not in {"", "|", ">"}, f"missing simple frontmatter {key}")
        require("TODO" not in match.group(1), f"unfinished frontmatter {key}")
    for md in root.rglob("*.md"):
        require(not md.is_symlink(), f"symlink forbidden: {md}")
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", md.read_text(encoding="utf-8")):
            target = target.strip().split(" \"", 1)[0].strip("<>")
            if urlparse(target).scheme or target.startswith("#"):
                continue
            target = unquote(target.split("#", 1)[0])
            if not target:
                continue
            # Links may use ../ within the package, but may never escape it.
            linked = md.parent / target
            for component in [linked, *linked.parents]:
                if component == root:
                    break
                require(not component.is_symlink(), f"symlink forbidden in Markdown link: {target}")
            require(linked.resolve().is_relative_to(root), f"Markdown link escapes package: {target}")
            local_file(root, linked.resolve().relative_to(root).as_posix())
    registry(read_json(root / "registry/skills.json", 1024 * 1024))
    index = root / "registry/index.json"
    if index.exists() or index.is_symlink():
        value = read_json(local_file(root, "registry/index.json"), 1024 * 1024)
        require(isinstance(value, dict) and type(value.get('schema_version')) is int
                and value['schema_version'] == 2 and 'records' in value,
                'optional registry index must be a Schema 2 index')
        registry(value, root / "registry")
