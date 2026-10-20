"""Shared shape, path, hashing and read-only JSON primitives."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from datetime import date, datetime
from urllib.parse import urlparse

HEX = re.compile(r"[0-9a-f]{64}\Z")


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def shape(value, keys, label):
    require(isinstance(value, dict) and set(value) == set(keys.split()),
            f"{label}: expected fields {keys}")


def shape_extended(value, keys, label, optional=""):
    """Required fields plus a bounded whitelist of optional fields.

    Backward compatible: a value carrying only the required fields stays
    valid. Forward compatible: a value carrying whitelisted optional fields
    is valid too. Unknown fields are still rejected, so a typo or an
    unrecognised record never passes silently.
    """
    required = set(keys.split())
    allowed = required | set(optional.split())
    require(isinstance(value, dict), f"{label}: expected object")
    require(required <= set(value), f"{label}: expected fields {keys}")
    unknown = set(value) - allowed
    require(not unknown, f"{label}: expected fields {keys}")


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
