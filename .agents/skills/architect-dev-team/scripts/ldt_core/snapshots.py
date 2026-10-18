"""Read-only Git/filesystem inventories with fail-closed coverage."""
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess

from .common import Invalid, require, path_text, relative, local_file, digest_file

MANAGED = {".git", ".architect-dev-team", "__pycache__"}
WALK_IGNORED = MANAGED | {"node_modules", ".venv", "venv", "dist", "build"}


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
