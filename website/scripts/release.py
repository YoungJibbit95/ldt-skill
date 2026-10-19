"""Build and validate inert website archives; never execute downloaded files."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import tarfile

REPOSITORY = "YoungJibbit95/ldt-skill"
WORKFLOW = ".github/workflows/website.yml"
IDENTITY = "release.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(value):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value), "Expected a full source SHA")
    return value


def positive(value):
    require(type(value) is int and value > 0, "Expected a positive integer identifier")
    return value


def safe_name(name):
    require(isinstance(name, str) and name and "\\" not in name and ":" not in name,
            "Unsafe archive path")
    p = PurePosixPath(name)
    require(not p.is_absolute() and all(x not in ("", ".", "..") for x in name.split("/")),
            "Unsafe archive path")
    reserved = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}
    require(not any(ord(char) < 32 for char in name) and all(
        part[-1] not in " ." and part.split(".")[0].lower() not in reserved for part in name.split("/")),
        "Archive path is unsafe on supported operating systems")
    return name


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique)


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def pack(dist, output, source_sha, run_id, attempt, tools, evidence):
    sha(source_sha)
    positive(run_id)
    positive(attempt)
    require(dist.is_dir() and not output.exists(), "Use an existing dist and a new output directory")
    files = {}
    for path in sorted(dist.rglob("*")):
        require(not path.is_symlink(), "Symlinks are forbidden in dist")
        if path.is_file():
            name = safe_name(path.relative_to(dist).as_posix())
            require(name != IDENTITY, "dist already contains release identity")
            files[name] = path.read_bytes()
    require("de/index.html" in files and "en/index.html" in files and "404.html" in files,
            "The candidate must contain both languages and the 404 page")
    identity = {"schema": 1, "repository": REPOSITORY, "source_sha": source_sha,
                "run_id": run_id, "run_attempt": attempt}
    files[IDENTITY] = (json.dumps(identity, sort_keys=True) + "\n").encode()
    output.mkdir(parents=True)
    archive = output / "site.tar.gz"
    with tarfile.open(archive, "w:gz", format=tarfile.USTAR_FORMAT) as tar:
        for name, data in sorted(files.items()):
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(data), 0o644, 0
            tar.addfile(info, io.BytesIO(data))
    manifest = {**identity, "workflow": WORKFLOW, "archive": archive.name,
                "archive_sha256": digest(archive.read_bytes()), "tools": tools,
                "files": {name: digest(data) for name, data in sorted(files.items())},
                "evidence": evidence}
    write_json(output / "manifest.json", manifest)
    return manifest


def verify(archive, manifest_path, trusted_path, expected_sha, expected_archive, extract=None, expected_manifest=None):
    """Trusted metadata must come separately from the GitHub API, never the archive."""
    sha(expected_sha)
    require(re.fullmatch(r"[0-9a-f]{64}", expected_archive or ""), "Expected approved archive SHA-256")
    if expected_manifest:
        require(digest(manifest_path.read_bytes()) == expected_manifest, "Manifest hash differs from approval")
    m, trusted = read_json(manifest_path), read_json(trusted_path)
    run, artifact = trusted["run"], trusted["artifact"]
    require(run["repository"]["full_name"] == REPOSITORY, "Wrong origin repository")
    require(run["head_repository"]["full_name"] == REPOSITORY, "Fork candidates cannot be deployed")
    require(run["path"] == WORKFLOW and run["event"] in ("push", "workflow_dispatch"), "Wrong origin workflow/event")
    require(run["status"] == "completed" and run["conclusion"] == "success", "Origin run did not succeed")
    require(run["head_sha"] == expected_sha, "Origin source SHA differs from approval")
    positive(run["id"])
    positive(run["run_attempt"])
    positive(artifact["id"])
    require(artifact["name"] == "website-candidate" and artifact["expired"] is False, "Invalid/expired artifact")
    require(artifact["workflow_run"]["id"] == run["id"] and artifact["workflow_run"]["head_sha"] == expected_sha,
            "Artifact belongs to a different run or SHA")
    require(m["schema"] == 1 and m["repository"] == REPOSITORY and m["workflow"] == WORKFLOW,
            "Wrong manifest schema/repository/workflow")
    require(m["source_sha"] == expected_sha and m["run_id"] == run["id"] and m["run_attempt"] == run["run_attempt"],
            "Manifest identity differs from trusted metadata")
    require(archive.stat().st_size <= 250_000_000, "Compressed archive exceeds size limit")
    require(m["archive"] == "site.tar.gz" and digest(archive.read_bytes()) == m["archive_sha256"] == expected_archive,
            "Archive hash differs from manifest/approval")
    require(isinstance(m["tools"], dict) and all(m["tools"].get(k) for k in ("node", "python", "lighthouse", "chromium")),
            "Missing tool versions")
    require(m["tools"]["lighthouse"] == "13.5.0", "Unexpected Lighthouse version")
    require(isinstance(m["evidence"], dict) and m["evidence"].get("source_sha") == expected_sha
            and m["evidence"].get("local_performance") == "passed"
            and m["evidence"].get("required_jobs") == "passed", "Missing same-revision evidence")
    require(isinstance(m["files"], dict) and m["files"], "Missing file inventory")
    data = {}
    portable_names = set()
    total = 0
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar:
            name = safe_name(member.name)
            require(member.isfile() and name.casefold() not in portable_names, "Links, directories and duplicate archive members are forbidden")
            portable_names.add(name.casefold())
            total += member.size
            require(len(data) < 20000 and total <= 250_000_000, "Archive exceeds size limits")
            data[name] = tar.extractfile(member).read()
    require(all(not any(parent.as_posix().casefold() in portable_names for parent in PurePosixPath(name).parents
                        if parent.as_posix() != ".") for name in data), "File/directory collision in archive")
    require({name: digest(body) for name, body in data.items()} == m["files"], "Archive inventory differs from manifest")
    expected_identity = {k: m[k] for k in ("schema", "repository", "source_sha", "run_id", "run_attempt")}
    require(json.loads(data[IDENTITY]) == expected_identity, "Public release identity differs from manifest")
    require(all(name in data for name in ("de/index.html", "en/index.html", "404.html")), "Missing entry pages")
    if extract:
        require(not extract.exists(), "Extraction destination must not exist")
        extract.mkdir(parents=True)
        # All names and bytes have been checked before the first write.
        for name, body in data.items():
            destination = extract / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(body)
    return m


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("pack")
    create.add_argument("--dist", type=Path, required=True)
    create.add_argument("--output", type=Path, required=True)
    create.add_argument("--sha", required=True)
    create.add_argument("--run-id", type=int, required=True)
    create.add_argument("--attempt", type=int, required=True)
    create.add_argument("--tools", type=Path, required=True)
    create.add_argument("--evidence", type=Path, required=True)
    check = sub.add_parser("verify")
    for name in ("archive", "manifest", "trusted"):
        check.add_argument("--" + name, type=Path, required=True)
    check.add_argument("--sha", required=True)
    check.add_argument("--archive-hash", required=True)
    check.add_argument("--manifest-hash")
    check.add_argument("--extract", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "pack":
            result = pack(args.dist, args.output, args.sha, args.run_id, args.attempt,
                          read_json(args.tools), read_json(args.evidence))
        else:
            result = verify(args.archive, args.manifest, args.trusted, args.sha,
                            args.archive_hash, args.extract, args.manifest_hash)
        print(json.dumps({"source_sha": result["source_sha"], "archive_sha256": result["archive_sha256"]}))
    except (ValueError, KeyError, TypeError, OSError, tarfile.TarError) as error:
        parser.exit(1, f"Release rejected: {error}\n")


if __name__ == "__main__":
    main()
