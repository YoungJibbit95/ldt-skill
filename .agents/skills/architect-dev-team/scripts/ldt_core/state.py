"""State validation, gate composition and explicit legacy migration."""
import copy
import json
from pathlib import Path
import re

from .common import (Invalid, require, shape, string, strings, hash_value, timestamp,
                     digest_file, local_file, read_json, relative, canonical, digest_bytes)
from .approvals import scope_fields, scope, approval
from .snapshots import snapshot

PHASES = {"INTAKE", "DISCOVERY", "SPECIFICATION", "ARCHITECTURE", "APPROVAL",
          "IMPLEMENTATION", "VERIFICATION", "PR_REVIEW", "NEXT_ITERATION"}


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
