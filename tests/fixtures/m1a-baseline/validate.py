#!/usr/bin/env python3
"""Read-only integrity checks for architect-dev-team (Python 3.10+, stdlib only)."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
from datetime import date, datetime
from urllib.parse import unquote, urlparse


class Invalid(ValueError):
    pass


HEX = re.compile(r"[0-9a-f]{64}\Z")
PHASES = {"INTAKE", "DISCOVERY", "SPECIFICATION", "ARCHITECTURE", "APPROVAL",
          "IMPLEMENTATION", "VERIFICATION", "PR_REVIEW", "NEXT_ITERATION"}
MANAGED = {".git", ".architect-dev-team", "__pycache__"}
WALK_IGNORED = MANAGED | {"node_modules", ".venv", "venv", "dist", "build"}


def require(condition, message):
    if not condition:
        raise Invalid(message)


def shape(value, keys, label):
    require(isinstance(value, dict) and set(value) == set(keys.split()),
            f"{label}: expected fields {keys}")


def string(value, label):
    require(isinstance(value, str) and bool(value.strip()), f"{label}: expected nonempty string")


def strings(value, label, nonempty=False):
    require(isinstance(value, list) and (bool(value) or not nonempty), f"{label}: expected list")
    for item in value:
        string(item, label)


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def hash_value(value, label):
    require(isinstance(value, str) and HEX.fullmatch(value), f"{label}: expected lowercase SHA256")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path, limit):
    with Path(path).open("rb") as stream:
        data = stream.read(limit + 1)
    require(len(data) <= limit, f"{path}: exceeds {limit} byte limit")
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=unique_object,
                          parse_constant=lambda value: (_ for _ in ()).throw(Invalid(f"invalid JSON number: {value}")))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise Invalid(f"{path}: invalid JSON ({exc})") from None


def relative(value):
    string(value, "path")
    path_text(value)
    require("\\" not in value and ":" not in value and not value.startswith("/")
            and all(part not in {"", ".", ".."} for part in value.split("/")),
            f"unsafe relative path: {value}")
    return PurePosixPath(value)


def path_text(value):
    require("\x00" not in value,
            f"unsupported NUL in path {ascii(value)}; remove the NUL before automated verification")
    try:
        value.encode("utf-8", "strict")
    except UnicodeError:
        raise Invalid(f"unsupported non-UTF8 path {ascii(value)}; rename it using a UTF-8 name before automated verification") from None


def local_file(root, value):
    rel = relative(value)
    path = root.joinpath(*rel.parts)
    for component in [path, *path.parents]:
        if component == root:
            break
        require(not component.is_symlink(), f"symlink forbidden: {value}")
    require(path.resolve().is_relative_to(root), f"path escapes root: {value}")
    require(path.is_file(), f"missing file: {value}")
    return path


def digest_file(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def git(root, *args):
    # Repository fsmonitor settings can otherwise launch a configured executable.
    return subprocess.run(["git", "-c", "core.fsmonitor=false", "-C", str(root), *args], capture_output=True,
                          check=False, timeout=30)


def file_metadata(path):
    metadata = path.stat()
    require(stat.S_ISREG(metadata.st_mode), f"unsupported file type: {path.name}")
    return {"type": "regular", "executable_bits": metadata.st_mode & 0o111 if os.name == "posix" else None}


def snapshot(root, schema_version=2):
    require(type(schema_version) is int and schema_version in {1, 2}, "snapshot schema_version must be 1 or 2")
    root = Path(root).resolve(strict=True)
    path_text(str(root))
    require(root.is_dir(), "snapshot root must be a directory")
    try:
        top = git(root, "rev-parse", "--show-toplevel")
    except FileNotFoundError:
        top = None
    paths = []
    index = {}
    head = None
    if top is not None and top.returncode == 0:
        require(Path(os.fsdecode(top.stdout).strip()).resolve() == root,
                "project root must equal Git toplevel")
        revision = git(root, "rev-parse", "--verify", "HEAD^{commit}")
        if revision.returncode == 0:
            head = revision.stdout.decode("ascii").strip()
            require(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", head), "invalid Git HEAD")
        else:
            # A symbolic HEAD with no referenced branch is the normal unborn case.
            symbolic = git(root, "symbolic-ref", "-q", "HEAD")
            require(symbolic.returncode == 0, "Git HEAD inspection failed; manual verification required")
            branch = symbolic.stdout.decode("utf-8", "strict").strip()
            exists = git(root, "show-ref", "--verify", "--quiet", branch)
            require(exists.returncode == 1, "Git HEAD inspection failed; manual verification required")
        staged = git(root, "ls-files", "--stage", "-z")
        require(staged.returncode == 0 and not staged.stderr,
                "git index inspection failed or reported diagnostics; manual verification required")
        for record in staged.stdout.split(b"\0"):
            if not record:
                continue
            metadata, raw = record.split(b"\t", 1)
            value = os.fsdecode(raw)
            path_text(value)
            mode, blob, stage = metadata.decode("ascii").split()
            require(stage == "0", f"{value}: unmerged Git index stage {stage}; manual resolution required")
            require(mode != "160000", f"{value}: unsupported submodule/gitlink; manual verification required; automated review/advance unavailable")
            index[value] = {"mode": mode, "blob": blob, "stage": int(stage)}
        listed = git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
        require(listed.returncode == 0 and not listed.stderr,
                "git ls-files failed or reported diagnostics; inventory may be incomplete; restore access and retry automated verification")
        for raw in listed.stdout.split(b"\0"):
            if raw:
                value = os.fsdecode(raw)
                path_text(value)
                if not MANAGED.intersection(PurePosixPath(value).parts):
                    paths.append(value)
    else:
        # Existing Git metadata must never silently downgrade to a non-Git snapshot.
        require(not (root / ".git").exists(), "Git metadata exists but Git inspection failed")
        def walk_error(error):
            raise Invalid(f"snapshot traversal failed at {ascii(error.filename)}: {error.strerror}; restore access before automated verification") from error
        for directory, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
            for name in dirs + files:
                path_text(name)
            dirs[:] = sorted(name for name in dirs if name not in WALK_IGNORED)
            for name in dirs:
                require(not (Path(directory) / name).is_symlink(), f"symlink forbidden: {name}")
            paths.extend((Path(directory) / name).relative_to(root).as_posix() for name in files)
    files = []
    for value in sorted(set(paths)):
        path = root.joinpath(*relative(value).parts)
        # Schema 2 retains index metadata even when a tracked worktree file is absent.
        require(not path.is_symlink(), f"symlink forbidden: {value}")
        if not path.exists():
            if schema_version == 2 and value in index:
                files.append({"path": value, "sha256": None, "type": "missing", "executable_bits": None,
                              "git_index": index[value]})
            continue
        source = local_file(root, value)
        metadata = file_metadata(source)
        item = {"path": value, "sha256": digest_file(source)}
        if schema_version == 2:
            item.update(metadata)
            item["git_index"] = index.get(value)
        files.append(item)
    return {"schema_version": schema_version, "head_revision": head, "files": files}


def iso_date(value, label):
    string(value, label)
    try:
        require(date.fromisoformat(value).isoformat() == value, f"{label}: expected YYYY-MM-DD")
    except ValueError:
        raise Invalid(f"{label}: expected YYYY-MM-DD") from None


def timestamp(value):
    string(value, "recorded_at")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        require(parsed.tzinfo is not None and "T" in value, "recorded_at requires time and timezone")
    except ValueError:
        raise Invalid("recorded_at requires ISO8601 time and timezone") from None


def https(value, label):
    string(value, label)
    parsed = urlparse(value)
    require(parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username
            and not parsed.password and not parsed.fragment and not parsed.query,
            f"{label}: expected canonical HTTPS URL")


def registry(value):
    shape(value, "schema_version skills", "registry")
    require(type(value["schema_version"]) is int and value["schema_version"] == 1, "registry schema_version must be 1")
    require(isinstance(value["skills"], list), "skills must be a list")
    ids = set()
    for entry in value["skills"]:
        shape(entry, "id name description author maintainer repository path revision license use_cases compatibility trust last_review_date limitations installation evidence", "registry entry")
        for key in ("id", "name", "description", "author", "maintainer"):
            string(entry[key], key)
        require(entry["id"] not in ids, "duplicate registry ID")
        ids.add(entry["id"])
        https(entry["repository"], "repository")
        relative(entry["path"])
        require(isinstance(entry["revision"], str) and re.fullmatch(r"[0-9a-f]{40}", entry["revision"]), "revision must be immutable 40-character lowercase commit")
        shape(entry["license"], "spdx url attribution", "license")
        string(entry["license"]["spdx"], "license.spdx")
        string(entry["license"]["attribution"], "license.attribution")
        https(entry["license"]["url"], "license.url")
        for key in ("use_cases", "compatibility", "limitations"):
            strings(entry[key], key, key != "limitations")
        trust = entry["trust"]
        require(isinstance(trust, str) and trust in {"candidate", "reviewed", "tested", "approved", "deprecated", "blocked"}, "invalid trust")
        iso_date(entry["last_review_date"], "last_review_date")
        shape(entry["installation"], "instructions", "installation")
        string(entry["installation"]["instructions"], "installation.instructions")
        require(isinstance(entry["evidence"], list), "evidence must be list")
        kinds = set()
        for evidence in entry["evidence"]:
            shape(evidence, "kind reference summary date", "registry evidence")
            require(isinstance(evidence["kind"], str) and evidence["kind"] in {"provenance", "review", "test", "approval"}, "invalid evidence kind")
            kinds.add(evidence["kind"])
            string(evidence["reference"], "evidence.reference")
            string(evidence["summary"], "evidence.summary")
            iso_date(evidence["date"], "evidence.date")
        needed = {"provenance"}
        if trust in {"reviewed", "tested", "approved"}:
            needed.add("review")
        if trust in {"tested", "approved"}:
            needed.add("test")
        if trust == "approved":
            needed.add("approval")
        require(needed <= kinds, f"{entry['id']}: trust lacks {sorted(needed - kinds)} evidence")


def scope_fields(state):
    require(isinstance(state, dict) and all(key in state for key in ("schema_version", "architecture", "milestone", "profile")),
            "scope requires schema_version, architecture, milestone, and profile")
    version = state["schema_version"]
    require(type(version) is int and version in {1, 2}, "state schema_version must be 1 or 2")
    require(isinstance(state["profile"], str) and state["profile"] in {"lean", "balanced", "rigorous"}, "invalid profile")
    if state["architecture"] is not None:
        shape(state["architecture"], "path sha256", "architecture")
        relative(state["architecture"]["path"])
        hash_value(state["architecture"]["sha256"], "architecture.sha256")
    milestone = state["milestone"]
    if milestone is not None:
        shape(milestone, "id summary acceptance" + (" required_checks" if version == 2 else ""), "milestone")
        string(milestone["id"], "milestone.id")
        string(milestone["summary"], "milestone.summary")
        strings(milestone["acceptance"], "milestone.acceptance", True)
        if version == 2:
            strings(milestone["required_checks"], "milestone.required_checks", True)
            require(len(set(milestone["required_checks"])) == len(milestone["required_checks"]), "duplicate required check name")


def scope(state):
    scope_fields(state)
    return digest_bytes(canonical({"architecture": state["architecture"], "milestone": state["milestone"], "profile": state["profile"]}))


def approval(state, kind, review=None):
    decisions = [item for item in state["approvals"] if item["kind"] == kind]
    require(bool(decisions), f"missing {kind} approval")
    latest = decisions[-1]  # Append order is authoritative; timestamps are evidence only.
    require(latest["decision"] == "approved", f"latest {kind} decision is rejected")
    require(latest["scope_sha256"] == scope(state), f"stale {kind} approval scope")
    if kind == "iteration":
        require(latest["review_sha256"] == review, "stale iteration review approval")


def artifact(root, value, label):
    shape(value, "path sha256", label)
    hash_value(value["sha256"], label)
    require(digest_file(local_file(root, value["path"])) == value["sha256"], f"{label} artifact changed")


def state(value, root, gate=None, *, migrating=False):
    root = Path(root).resolve(strict=True)
    require(root.is_dir(), "project root must be a directory")
    shape(value, "schema_version phase approval_stage profile architecture milestone approvals checks review completed open_issues constraints next_action", "state")
    scope_fields(value)
    version = value["schema_version"]
    require(isinstance(value["phase"], str) and value["phase"] in PHASES, "invalid phase")
    stage = value["approval_stage"]
    require(stage is None or (isinstance(stage, str) and stage in {"architecture", "iteration"}), "invalid approval_stage")
    require((value["phase"] == "APPROVAL") == (stage is not None), "approval_stage required only in APPROVAL")
    if version == 1 and not migrating and (gate is not None or value["phase"] in {"IMPLEMENTATION", "VERIFICATION", "PR_REVIEW", "NEXT_ITERATION"} or stage == "iteration"):
        raise Invalid("legacy schema v1 cannot satisfy gates; run migrate-state with explicit --required-check policy, then obtain renewed architecture approval")
    require(isinstance(value["profile"], str) and value["profile"] in {"lean", "balanced", "rigorous"}, "invalid profile")
    if value["architecture"] is not None:
        artifact(root, value["architecture"], "architecture")
    if stage == "architecture":
        require(value["architecture"] is not None and value["milestone"] is not None,
                "architecture approval stage requires architecture and milestone")
    require(isinstance(value["approvals"], list), "approvals must be list")
    for item in value["approvals"]:
        shape(item, "kind decision scope_sha256 review_sha256 evidence recorded_at", "approval")
        require(isinstance(item["kind"], str) and item["kind"] in {"architecture", "iteration"}, "invalid approval kind")
        require(isinstance(item["decision"], str) and item["decision"] in {"approved", "rejected"}, "invalid decision")
        hash_value(item["scope_sha256"], "scope_sha256")
        if item["review_sha256"] is not None:
            hash_value(item["review_sha256"], "review_sha256")
        require((item["kind"] == "architecture") == (item["review_sha256"] is None), "iteration decisions require review hash; architecture decisions require null")
        string(item["evidence"], "approval.evidence")
        timestamp(item["recorded_at"])
    require(isinstance(value["checks"], list), "checks must be list")
    names = set()
    for item in value["checks"]:
        shape(item, "name required status evidence waiver", "check")
        string(item["name"], "check.name")
        require(item["name"] not in names, "duplicate check name")
        names.add(item["name"])
        require(type(item["required"]) is bool, "check.required must be boolean")
        require(isinstance(item["status"], str) and item["status"] in {"passed", "failed", "unavailable", "not_run", "waived"}, "invalid check status")
        require(isinstance(item["evidence"], str), "check.evidence must be string")
        if item["status"] in {"passed", "failed", "waived"}:
            string(item["evidence"], "check.evidence")
        if item["status"] == "waived":
            shape(item["waiver"], "evidence reason" + (" scope_sha256" if version == 2 else ""), "waiver")
            string(item["waiver"]["evidence"], "waiver.evidence")
            string(item["waiver"]["reason"], "waiver.reason")
            if version == 2:
                hash_value(item["waiver"]["scope_sha256"], "waiver.scope_sha256")
                require(item["waiver"]["scope_sha256"] == scope(value), "stale waiver scope; renewed explicit waiver required")
        else:
            require(item["waiver"] is None, "only waived checks may carry a waiver; failed checks cannot be waived")
    if value["review"] is not None:
        review = value["review"]
        shape(review, "path sha256 independence evidence", "review")
        artifact(root, {key: review[key] for key in ("path", "sha256")}, "review")
        require(isinstance(review["independence"], str) and review["independence"] in {"independent", "self", "unavailable"}, "invalid review independence")
        string(review["evidence"], "review.evidence")
        saved = read_json(local_file(root, review["path"]), 16 * 1024 * 1024)
        if migrating:
            shape(saved, "schema_version head_revision files", "legacy review snapshot")
            require(type(saved["schema_version"]) is int and saved["schema_version"] == 1,
                    "legacy review snapshot schema_version must be 1")
            require(saved["head_revision"] is None or (isinstance(saved["head_revision"], str) and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", saved["head_revision"])), "invalid legacy review HEAD")
            require(isinstance(saved["files"], list), "legacy review files must be list")
            for item in saved["files"]:
                shape(item, "path sha256", "legacy review file")
                relative(item["path"])
                hash_value(item["sha256"], "legacy review file hash")
        if not migrating:
            actual = snapshot(root, version)
            require(canonical(saved) == canonical(actual), "review snapshot is stale or incomplete (current schema coverage required)")
    for key in ("completed", "open_issues", "constraints"):
        strings(value[key], key)
    string(value["next_action"], "next_action")
    automatic = None
    if value["phase"] in {"IMPLEMENTATION", "VERIFICATION"}:
        automatic = "implement"
    elif value["phase"] == "PR_REVIEW" or stage == "iteration":
        automatic = "review"
    elif value["phase"] == "NEXT_ITERATION":
        automatic = "advance"
    levels = {None: 0, "implement": 1, "review": 2, "advance": 3}
    required = 0 if migrating else max(levels[gate], levels[automatic])
    if required:
        require(value["architecture"] is not None and value["milestone"] is not None, "gate requires architecture and milestone")
        approval(value, "architecture")
        policy = set(value["milestone"]["required_checks"])
        actual_policy = {item["name"] for item in value["checks"] if item["required"]}
        require(actual_policy == policy, "checks must match approved required_checks exactly; missing, renamed, demoted or additional mandatory check")
    if required >= 2:
        mandatory = [item for item in value["checks"] if item["required"]]
        require(bool(mandatory), "review requires nonempty mandatory checks")
        require(all(item["status"] in {"passed", "waived"} for item in mandatory), "mandatory checks block review")
        require(value["review"] is not None, "review snapshot required")
        if value["profile"] == "rigorous":
            independence_waived = any(item["name"] == "independent_review" and item["status"] == "waived"
                                      for item in mandatory)
            require(value["review"]["independence"] == "independent" or independence_waived,
                    "rigorous review requires independent review or a required independent_review check explicitly waived")
    if required >= 3:
        approval(value, "iteration", value["review"]["sha256"])


def migrate_state(value, root, required_checks):
    """Return a proposal only: old decisions remain historical, never reapproved."""
    require(isinstance(value, dict) and type(value.get("schema_version")) is int and value["schema_version"] == 1,
            "migrate-state requires legacy schema v1 input")
    state(value, root, migrating=True)
    strings(required_checks, "required checks")
    require(len(set(required_checks)) == len(required_checks), "duplicate required check name")
    require(bool(required_checks) if value["milestone"] is not None else not required_checks,
            "migration with a milestone requires explicit --required-check names; without a milestone omit them")
    result = copy.deepcopy(value)
    prefix = ("Schema v1 migration audit (historical evidence only): "
              f"legacy_state_sha256={digest_bytes(canonical(value))}; scope_sha256={scope(value)}; "
              f"review_sha256={value['review']['sha256'] if value['review'] else None}; ")
    detail = json.dumps({"review": value["review"], "checks": value["checks"]}, sort_keys=True, ensure_ascii=True)
    marker = " [summary truncated; retain original state using legacy_state_sha256]"
    remaining = 4096 - len(prefix)
    if len(detail) > remaining:
        detail = detail[:remaining - len(marker)] + marker
    result["completed"].append(prefix + detail)
    result["schema_version"] = 2
    if result["milestone"] is not None:
        result["milestone"]["required_checks"] = list(required_checks)
    for item in result["checks"]:
        item.update(required=item["name"] in required_checks, status="not_run", evidence="Migration invalidated prior check results; rerun after reapproval.", waiver=None)
    existing = {item["name"] for item in result["checks"]}
    result["checks"].extend({"name": name, "required": True, "status": "not_run", "evidence": "", "waiver": None}
                            for name in required_checks if name not in existing)
    result["review"] = None
    design_ready = result["architecture"] is not None and result["milestone"] is not None
    result["phase"] = "APPROVAL" if design_ready else "INTAKE"
    result["approval_stage"] = "architecture" if design_ready else None
    result["next_action"] = "Obtain renewed human architecture approval for the schema v2 scope and explicit required_checks policy before implementation."
    state(result, root)
    require(len(canonical(result)) <= 64 * 1024,
            "migrated state exceeds 65536 byte limit; compact the original completed/open_issues/constraints evidence while retaining historical approval records, then retry migration")
    return result


def package(root):
    root = Path(root).resolve(strict=True)
    required = ["SKILL.md", "agents/openai.yaml", "registry/skills.json", "assets/state.template.json",
                "assets/architecture.template.md", "scripts/validate.py"]
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


def main(argv=None):
    # Keep emitted JSON and diagnostics portable when the host console uses a
    # legacy encoding. Imports do not change the embedding application's streams.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("package", "registry", "digest", "scope"):
        commands.add_parser(name).add_argument("path")
    state_parser = commands.add_parser("state")
    state_parser.add_argument("path")
    state_parser.add_argument("--root", required=True)
    state_parser.add_argument("--gate", choices=("implement", "review", "advance"))
    migration_parser = commands.add_parser("migrate-state")
    migration_parser.add_argument("path")
    migration_parser.add_argument("--root", required=True)
    migration_parser.add_argument("--required-check", action="append", default=[], metavar="NAME")
    commands.add_parser("snapshot").add_argument("root")
    args = parser.parse_args(argv)
    try:
        if args.command == "digest":
            print(digest_file(args.path))
        elif args.command == "scope":
            value = read_json(args.path, 64 * 1024)
            print(scope(value))
        elif args.command == "migrate-state":
            print(canonical(migrate_state(read_json(args.path, 64 * 1024), args.root, args.required_check)).decode("utf-8"))
        elif args.command == "snapshot":
            print(canonical(snapshot(args.root)).decode("utf-8"))
        elif args.command == "registry":
            registry(read_json(args.path, 1024 * 1024))
            print("OK registry")
        elif args.command == "package":
            package(args.path)
            print("OK package")
        else:
            state(read_json(args.path, 64 * 1024), args.root, args.gate)
            print("OK state")
        return 0
    except (Invalid, OSError, UnicodeError, subprocess.SubprocessError, RecursionError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
