"""Exact approval subjects and ordered human-decision prerequisites."""
from .common import require, shape, string, strings, relative, hash_value, digest_bytes, canonical


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


APPROVAL_KINDS = ("architecture", "start", "iteration")


def approval(state, kind, review=None):
    decisions = [item for item in state["approvals"] if item["kind"] == kind]
    require(bool(decisions), f"missing {kind} approval")
    latest = decisions[-1]  # Append order is authoritative; timestamps are evidence only.
    require(latest["decision"] == "approved", f"latest {kind} decision is rejected")
    require(latest["scope_sha256"] == scope(state), f"stale {kind} approval scope")
    if kind == "iteration":
        require(latest["review_sha256"] == review, "stale iteration review approval")
    if kind == "start":
        # A start decision stands only on an approved architecture for the same
        # scope. It is an additional gate, not a replacement for it.
        approval(state, "architecture")
