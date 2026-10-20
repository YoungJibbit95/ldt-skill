"""
OpenCode runtime adapter: real native subagent dispatch and session evidence.

Python 3.10+, stdlib only. Every call is a documented OpenCode CLI invocation.
No invented APIs. When the runtime is unavailable the adapter reports
`unavailable` honestly instead of fabricating a result.
"""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

from .common import Invalid


# Role profile -> native OpenCode agent. The native agent's own permission set
# enforces the write boundary; we do not duplicate it.
#
#   research    -> explore  (read-only native agent: cannot write files)
#   implementer -> general  (subagent with write access)
#   critic      -> explore  (read-only native agent: cannot write production files)
#   architect   -> plan     (primary, read-only for edits)
#
# The mapping is exact, not a substring match: a role like "Planar Specialist"
# must not silently become a read-only agent.
ROLE_AGENT = {
    "research": "explore",
    "research specialist": "explore",
    "domain intelligence": "explore",
    "architect": "plan",
    "architecture lead": "plan",
    "implementer": "general",
    "implementation": "general",
    "backend": "general",
    "backend specialist": "general",
    "frontend": "general",
    "frontend specialist": "general",
    "integration": "general",
    "integration engineer": "general",
    "critic": "explore",
    "independent critic": "explore",
    "reviewer": "explore",
    # The lead merges the specialists' results, so the role needs write
    # access. The plan sub-phase overrides the agent with the read-only
    # `plan` agent so the lead cannot implement the work itself.
    "department lead": "general",
    "department_lead": "general",
    "lead": "general",
}

# Fallback when a role is unknown: an agent that may write, because an
# implementer must be able to. Critics and researchers use explicit roles.
DEFAULT_AGENT = "general"


@dataclass
class RuntimeInfo:
    """Detected OpenCode runtime."""
    available: bool
    executable: Optional[str] = None
    version: Optional[str] = None
    reason: Optional[str] = None
    agents: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    read_only_agents: list[str] = field(default_factory=list)
    agent_details_available: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentRun:
    """Result of one real native agent dispatch."""
    status: str  # completed | failed | blocked | unavailable
    session_id: Optional[str] = None
    agent: Optional[str] = None
    model: Optional[str] = None
    output: str = ""
    events: list[dict[str, Any]] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _candidate_executables() -> list[str]:
    """Known locations for the OpenCode CLI, PATH first."""
    candidates: list[str] = []
    found = shutil.which("opencode")
    if found:
        candidates.append(found)
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(str(Path(appdata) / "npm" / "opencode.cmd"))
        candidates.append(str(Path(appdata) / "npm" / "opencode"))
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates.append(str(Path(local) / "Programs" / "@opencodedesktop" / "cli" / "opencode.exe"))
    return candidates


def _run(cmd: list[str], timeout: int = 120, cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    """Run a command without a shell, capturing UTF-8 text output.

    The Windows console default (cp1252) cannot decode agent output, so the
    encoding is pinned and undecodable bytes are replaced rather than
    crashing the reader thread.
    """
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace",
                          cwd=str(cwd) if cwd else None, shell=False)


def _resolve_executable() -> Optional[str]:
    for candidate in _candidate_executables():
        if Path(candidate).exists():
            return candidate
    return None


def list_agents(executable: Optional[str] = None) -> list[str]:
    """List native agent IDs reported by the runtime."""
    exe = executable or _resolve_executable()
    if not exe:
        return []
    try:
        result = _run([exe, "debug", "agents"], timeout=90)
        data = json.loads(result.stdout)
        return sorted({str(item.get("id")) for item in data if item.get("id")})
    except Exception:
        return []


def list_models(executable: Optional[str] = None) -> list[str]:
    """List model IDs reported by the runtime."""
    exe = executable or _resolve_executable()
    if not exe:
        return []
    try:
        result = _run([exe, "models"], timeout=90)
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def agent_permissions(executable: Optional[str] = None) -> dict[str, dict[str, Any]]:
    """Read the native agent permission sets from the runtime.

    Returns a mapping of agent id to its recorded permission list. The
    permission data is what makes the read-only claim verifiable instead of
    a constant in this file.
    """
    exe = executable or _resolve_executable()
    if not exe:
        return {}
    try:
        result = _run([exe, "debug", "agents"], timeout=90)
        data = json.loads(result.stdout)
    except Exception:
        return {}
    details: dict[str, dict[str, Any]] = {}
    for item in data:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        details[str(item["id"])] = {
            "mode": item.get("mode"),
            "permissions": item.get("permissions") or [],
        }
    return details


def read_only_agents(executable: Optional[str] = None) -> set[str]:
    """Agents whose native permission set denies every write action.

    Derived from the runtime's own permission data: an agent is read-only
    when it carries a deny-all rule (``action: "*"``) or denies the write
    actions. When the runtime cannot be queried the set is empty, so the
    caller must not assume a write boundary.
    """
    details = agent_permissions(executable)
    if not details:
        return set()
    result: set[str] = set()
    for agent_id, info in details.items():
        permissions = info.get("permissions") or []
        denies_write = False
        deny_all = False
        for rule in permissions:
            if not isinstance(rule, dict):
                continue
            action = str(rule.get("action", ""))
            effect = str(rule.get("effect", ""))
            if effect != "deny":
                continue
            if action == "*":
                deny_all = True
            elif action in {"edit", "write", "patch", "bash", "shell"}:
                denies_write = True
        if deny_all or denies_write:
            result.add(agent_id)
    return result


def is_read_only_agent(agent: str, executable: Optional[str] = None) -> bool:
    """True when the native agent cannot write files.

    The answer comes from the runtime's own permission data. When the
    runtime cannot be queried the answer is False: an unverified agent must
    never be treated as a write boundary, and a review that depends on one
    stays unavailable.
    """
    verified = read_only_agents(executable)
    if not verified:
        return False
    return agent in verified


def detect_runtime(refresh: bool = False) -> RuntimeInfo:
    """Detect the OpenCode CLI, its version, agents and models."""
    for candidate in _candidate_executables():
        if not Path(candidate).exists():
            continue
        try:
            version = _run([candidate, "--version"], timeout=30).stdout.strip()
            if not refresh:
                return RuntimeInfo(True, candidate, version, None, [], [])
            agents = list_agents(candidate)
            models = list_models(candidate)
            ro = sorted(read_only_agents(candidate))
            return RuntimeInfo(True, candidate, version, None, agents, models, ro,
                               agent_details_available=bool(agents))
        except Exception as exc:
            return RuntimeInfo(False, candidate, None, f"probe failed: {exc}")
    return RuntimeInfo(False, None, None, "opencode CLI not found on PATH or known locations")


def model_candidates(profile: str, available: Optional[list[str]] = None) -> list[str]:
    """Ordered model fallback chain for a role profile.

    The chain is intersected with the models the runtime actually reports, so
    an unavailable or unauthorized provider is simply skipped. Order expresses
    capability preference (stronger reasoning first), not price alone.
    Listing a model does not prove it is usable, so the caller still handles
    provider errors and continues down the chain.
    """
    models = available if available is not None else list_models()
    if not models:
        return []
    preferred = {
        "high": ("nemotron-3.5-super-vl", "nemotron-3-ultra", "minimax-m3.1-flash",
                 "gpt-6.1-sol", "gpt-6-sol", "gpt-6-luna"),
        "medium": ("minimax-m3.1-flash", "nemotron-3.5-lightning",
                   "nemotron-3.5-super-vl", "gpt-6-luna", "gpt-5.6-terra"),
        "low": ("mimo-v2.6-flash", "beam-free", "longcat-2.5-preview",
                "glm-5.3-flash", "deepseek-v4.1-flash", "minimax-m3.1-flash"),
    }
    needles = preferred.get(profile, preferred["medium"])
    chain: list[str] = []
    for needle in needles:
        for model in models:
            if needle.lower() in model.lower() and model not in chain:
                chain.append(model)
                break
    return chain


def resolve_model(profile: str, available: Optional[list[str]] = None) -> Optional[str]:
    """First preferred model for a role profile that the runtime lists.

    Never invents an identifier. Returns None when nothing matches, so the
    caller can record an honest 'unassigned' state.
    """
    chain = model_candidates(profile, available)
    return chain[0] if chain else None


def agent_for_role(role: str) -> str:
    """Map an LDT role to a native OpenCode agent id.

    Exact match on a normalised role, then on the role's head noun. A
    substring match would route an implementer to a read-only agent.
    """
    key = " ".join(role.strip().lower().replace("_", " ").replace("-", " ").split())
    if key in ROLE_AGENT:
        return ROLE_AGENT[key]
    for candidate in ROLE_AGENT:
        if key.endswith(candidate):
            return ROLE_AGENT[candidate]
    return DEFAULT_AGENT


FIXTURE_ENV = "LDT_RUNTIME_FIXTURE"


def fixture_responses() -> Optional[dict[str, Any]]:
    """Load canned agent outputs when the test fixture environment is set.

    Fixture mode exists so deterministic tests can exercise the orchestration
    without live model calls. It is never silent: every run made this way is
    tagged execution_mode=fixture and is refused by independence checks.
    """
    path = os.environ.get(FIXTURE_ENV)
    if not path:
        return None
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise Invalid(f"invalid runtime fixture {path}: {exc}") from None
    return data if isinstance(data, dict) else None


def dispatch(
    prompt: str,
    role: str,
    cwd: Path,
    model_profile: str = "medium",
    model: Optional[str] = None,
    title: Optional[str] = None,
    session_id: Optional[str] = None,
    executable: Optional[str] = None,
    timeout: int = 900,
    agent: Optional[str] = None,
) -> AgentRun:
    """Run one real native OpenCode agent and capture verifiable evidence.

    The native agent's own permission set enforces the write boundary.
    A fresh session is created per dispatch unless session_id is given.
    """
    fixture = fixture_responses()
    if fixture is not None:
        return _fixture_run(fixture, role, prompt, title)

    exe = executable or _resolve_executable()
    if not exe:
        return AgentRun("unavailable", error="opencode CLI not found")

    agent = agent or agent_for_role(role)
    available = list_models(exe)

    # Model fallback chain. A model that is listed can still be unusable
    # (quota exhausted, unauthorized). We try in order and record the actual
    # model that ran, plus every fallback that was attempted and why.
    if model:
        chain = [model]
    else:
        chain = model_candidates(model_profile, available)
    fallbacks: list[dict[str, str]] = []

    started = _now()
    last_error = "no model candidate available"
    last_model: Optional[str] = None
    last_session: Optional[str] = session_id

    for candidate in chain:
        last_model = candidate
        run = _invoke(exe, agent, candidate, prompt, title, session_id, timeout, cwd)
        if run.status == "completed":
            run.evidence["model_fallbacks"] = fallbacks
            run.evidence["model_requested_profile"] = model_profile
            run.evidence["execution_mode"] = "native"
            run.duration_seconds = _now() - started
            return run
        last_error = run.error or "unknown provider error"
        last_session = run.session_id or last_session
        fallbacks.append({"model": candidate, "error": last_error[:500]})

    # Last resort: let the runtime use its configured default model.
    run = _invoke(exe, agent, None, prompt, title, session_id, timeout, cwd)
    if run.status == "completed":
        run.evidence["model_fallbacks"] = fallbacks
        run.evidence["model_requested_profile"] = model_profile
        run.evidence["model_used"] = "runtime-default"
        run.evidence["execution_mode"] = "native"
        run.duration_seconds = _now() - started
        return run
    last_error = run.error or last_error

    return AgentRun("failed", session_id=last_session, agent=agent,
                    model=last_model, error=last_error,
                    evidence={"model_fallbacks": fallbacks, "execution_mode": "native"},
                    duration_seconds=_now() - started)


def _now() -> float:
    return time.monotonic()


def _fixture_run(fixture: dict[str, Any], role: str, prompt: str, title: Optional[str]) -> AgentRun:
    """Produce a deterministic, clearly labelled fixture run.

    The result carries execution_mode=fixture so no downstream check can
    mistake it for native agent execution.
    """
    key = "research" if "research" in role.lower() else (
        "critic" if "critic" in role.lower() else "implementer")
    entry = fixture.get(key) or {}
    agent = entry.get("agent") or ("explore" if key in ("research", "critic") else "general")
    session_id = entry.get("session_id") or f"ses_fixture_{key}"
    status = entry.get("status", "completed")
    output = entry.get("output", "")
    if isinstance(output, (dict, list)):
        output = json.dumps(output)
    return AgentRun(
        status=status,
        session_id=session_id,
        agent=agent,
        model=entry.get("model", "fixture-model"),
        output=output,
        evidence={
            "execution_mode": "fixture",
            "fixture_key": key,
            "returncode": 0,
        },
    )


# The prompt travels through a .cmd wrapper, and the command line of a batch
# file is limited to 8191 characters. The limit is kept below it.
MAX_PROMPT_CHARS = 6000


def _bound_prompt(prompt: str) -> str:
    """A prompt that fits on a command line.

    The prompt travels as an argument, and an argument has a length limit.
    A prompt that is too long is cut, and the cut is visible to the agent,
    so it knows that it is not seeing everything.
    """
    if len(prompt) <= MAX_PROMPT_CHARS:
        return prompt
    keep = MAX_PROMPT_CHARS - 400
    return (prompt[:keep]
            + "\n\n[the rest of the assignment was cut: it did not fit on the "
              "command line. Ask for the missing part if you need it.]\n")


def _invoke(exe, agent, chosen_model, prompt, title, session_id, timeout, cwd) -> AgentRun:
    """One attempt to run a native agent with a specific model."""
    cmd = [exe, "run", "--agent", agent, "--format", "json"]
    if chosen_model:
        cmd += ["--model", chosen_model]
    if title:
        cmd += ["--title", title]
    if session_id:
        cmd += ["--session", session_id]
    cmd.append(_bound_prompt(prompt))

    try:
        result = _run(cmd, timeout=timeout, cwd=cwd)
    except subprocess.TimeoutExpired:
        return AgentRun("failed", agent=agent, model=chosen_model,
                        error="agent run timed out")
    except Exception as exc:
        return AgentRun("failed", agent=agent, model=chosen_model, error=str(exc))

    events: list[dict[str, Any]] = []
    texts: list[str] = []
    observed_session = session_id
    provider_error: Optional[str] = None
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        events.append(event)
        sid = event.get("sessionID")
        if sid:
            observed_session = sid
        if event.get("type") == "error":
            err = event.get("error") or {}
            provider_error = str(err.get("message") or err.get("type") or "provider error")
        part = event.get("part") or {}
        if isinstance(part, dict) and part.get("type") == "text" and part.get("text"):
            texts.append(str(part["text"]))

    if provider_error:
        return AgentRun("failed", session_id=observed_session, agent=agent,
                        model=chosen_model, error=provider_error,
                        events=events, evidence={"returncode": result.returncode})
    # A non-zero exit is a failure even when partial text was produced. The
    # agent did not finish; its output must not be recorded as a completed run.
    if result.returncode != 0:
        return AgentRun("failed", session_id=observed_session, agent=agent,
                        model=chosen_model,
                        error=(result.stderr.strip() or f"agent exited with {result.returncode}")[:2000],
                        events=events, evidence={"returncode": result.returncode})
    if not texts:
        return AgentRun("failed", session_id=observed_session, agent=agent,
                        model=chosen_model, error="agent produced no text output",
                        events=events, evidence={"returncode": result.returncode})

    return AgentRun(
        status="completed",
        session_id=observed_session,
        agent=agent,
        model=chosen_model,
        output="\n".join(texts),
        events=events,
        evidence={"returncode": result.returncode, "executable": exe,
                  "execution_mode": "native"},
    )


def verify_session(session_id: str, cwd: Optional[Path] = None) -> dict[str, Any]:
    """Verify a session exists in the runtime and return its recorded facts.

    This is the independent evidence used for critic-independence checks.
    """
    exe = _resolve_executable()
    if not exe:
        return {"verified": False, "reason": "opencode CLI not found"}
    if not session_id:
        return {"verified": False, "reason": "no session id recorded"}
    try:
        result = _run([exe, "session", "export", session_id], timeout=90, cwd=cwd)
    except Exception as exc:
        return {"verified": False, "reason": f"export failed: {exc}"}
    if result.returncode != 0:
        return {"verified": False, "reason": f"session export failed: {result.stderr.strip()[:200]}"}
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {"verified": False, "reason": f"session export not valid JSON: {exc}"}
    info = data.get("info") or {}
    agent = info.get("agent")
    return {
        "verified": True,
        "session_id": info.get("id", session_id),
        "agent": agent,
        "outcome": info.get("outcome"),
        "tokens": info.get("tokens"),
        "cost": info.get("cost"),
        "time": info.get("time"),
        "title": info.get("title"),
        "read_only_agent": bool(agent) and is_read_only_agent(str(agent)),
    }


def independence_report(
    implementer: AgentRun,
    critic: AgentRun,
    cwd: Optional[Path] = None,
) -> dict[str, Any]:
    """Determine whether a review is genuinely independent.

    Independence requires:
      1. Both runs completed against the real runtime. A failed or
         unavailable run is not a review.
      2. Distinct session IDs.
      3. Both sessions independently verifiable in the runtime.
      4. The critic ran under a read-only native agent, verified from the
         runtime's own permission data.

    A missing or duplicated artifact fails. Metadata alone never passes.
    """
    reasons: list[str] = []
    for label, run in (("implementer", implementer), ("critic", critic)):
        if run.status == "unavailable":
            reasons.append(f"runtime unavailable for the {label}")
        elif run.status != "completed":
            reasons.append(f"{label} run did not complete (status {run.status})")
    if implementer.evidence.get("execution_mode") == "fixture":
        reasons.append("implementer run is a fixture, not native agent execution")
    if critic.evidence.get("execution_mode") == "fixture":
        reasons.append("critic run is a fixture, not native agent execution")
    if not implementer.session_id or not critic.session_id:
        reasons.append("missing session id")
    elif implementer.session_id == critic.session_id:
        reasons.append("implementer and critic share the same session")

    impl_evidence = verify_session(implementer.session_id, cwd) if implementer.session_id else {"verified": False}
    critic_evidence = verify_session(critic.session_id, cwd) if critic.session_id else {"verified": False}
    if not impl_evidence.get("verified"):
        reasons.append(f"implementer session not verifiable: {impl_evidence.get('reason')}")
    if not critic_evidence.get("verified"):
        reasons.append(f"critic session not verifiable: {critic_evidence.get('reason')}")

    # The reviewer agent is the one the runtime recorded, not the one that
    # was requested. A requested read-only agent that actually ran writable
    # is a broken boundary.
    critic_agent = critic_evidence.get("agent") if critic_evidence.get("verified") else None
    if critic_agent and not is_read_only_agent(str(critic_agent)):
        reasons.append(f"critic agent '{critic_agent}' is not read-only")
    if (impl_evidence.get("verified") and critic_evidence.get("verified")
            and impl_evidence.get("agent") == critic_evidence.get("agent")
            and not is_read_only_agent(str(critic_evidence.get("agent")))):
        reasons.append("both roles ran under the same writable agent")

    return {
        "independence": "independent" if not reasons else "unavailable",
        "reasons": reasons,
        "implementer": {
            "session_id": implementer.session_id,
            "agent": impl_evidence.get("agent"),
            "requested_agent": implementer.agent,
            "model": implementer.model,
            "verified": impl_evidence.get("verified", False),
            "outcome": impl_evidence.get("outcome"),
            "tokens": impl_evidence.get("tokens"),
            "execution_mode": implementer.evidence.get("execution_mode", "native"),
        },
        "critic": {
            "session_id": critic.session_id,
            "agent": critic_agent,
            "requested_agent": critic.agent,
            "model": critic.model,
            "verified": critic_evidence.get("verified", False),
            "outcome": critic_evidence.get("outcome"),
            "tokens": critic_evidence.get("tokens"),
            "execution_mode": critic.evidence.get("execution_mode", "native"),
        },
    }
