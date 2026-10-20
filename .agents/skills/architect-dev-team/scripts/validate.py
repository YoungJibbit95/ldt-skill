#!/usr/bin/env python3
"""Read-only integrity checks for architect-dev-team (Python 3.10+, stdlib only)."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

# Support both normal execution and the existing importlib file-path workflow.
# Resolve the adjacent core explicitly, without changing the caller's sys.path.
_core_file = Path(__file__).resolve().parent / "ldt_core" / "__init__.py"
_core_name = "ldt_core"
_existing_core = sys.modules.get("ldt_core")
if _existing_core is not None and Path(getattr(_existing_core, "__file__", "") or "").resolve() != _core_file:
    # File-path imports of multiple skill versions must not mix approval rules.
    _core_name = "_architect_dev_team_core_" + hashlib.sha256(os.fsencode(_core_file)).hexdigest()
    _existing_core = sys.modules.get(_core_name)
if _existing_core is None:
    _spec = importlib.util.spec_from_file_location(_core_name, _core_file,
                                                 submodule_search_locations=[str(_core_file.parent)])
    _core = importlib.util.module_from_spec(_spec)
    sys.modules[_core_name] = _core
    try:
        _spec.loader.exec_module(_core)
    except BaseException:
        sys.modules.pop(_core_name, None)
        raise
elif Path(getattr(_existing_core, "__file__", "") or "").resolve() != _core_file:
    raise ImportError("core namespace collision; refusing to mix skill copies")
else:
    _core = _existing_core

# Compatibility exports; validation rules live only in the adjacent core.
for _name in _core.__all__:
    globals()[_name] = getattr(_core, _name)


def critic_report_cli(root, action, task_id=None):
    """Validate a stored critic report against the contract it belongs to."""
    from pathlib import Path as _Path
    if action != "validate":
        print(f"Unknown critic-report action: {action}", file=sys.stderr)
        return 1
    if not task_id:
        print("INVALID: --task-id is required", file=sys.stderr)
        return 1
    from ldt_core.task_contracts import load_contract
    from ldt_core.critic_report import CriticReport, validate_critic_report
    try:
        contract = load_contract(_Path(root), task_id)
    except Invalid as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    stored = getattr(contract, "critic_report", None)
    if not stored:
        print("INVALID: this critic contract carries no report", file=sys.stderr)
        return 1
    report = CriticReport.from_dict(stored)
    # The revision the report claims must still be the current one.
    current = ""
    try:
        from ldt_core.pair_execution import _current_revision
        current = _current_revision(_Path(root))
    except Exception as exc:
        print(f"INVALID: cannot determine the current revision: {exc}", file=sys.stderr)
        return 1
    errors = validate_critic_report(
        report,
        expected_task_id=contract.task_id,
        expected_reviewed_task_id=contract.review_target,
        expected_revision=current,
        required_checks=list(contract.required_checks or []),
    )
    # The reviewer session must still exist in the runtime.
    if report.reviewer.session_id:
        from ldt_core.runtime import verify_session
        evidence = verify_session(report.reviewer.session_id, _Path(root))
        if not evidence.get("verified"):
            errors.append("the reviewer session is no longer verifiable in the runtime")
        else:
            report.reviewer.verified = True
            report.reviewer.read_only_agent = bool(evidence.get("read_only_agent"))
            if not report.reviewer.read_only_agent:
                errors.append("the reviewer agent is not read-only")
    if errors:
        for reason in errors:
            print(f"INVALID: {reason}")
        return 1
    print("OK critic report")
    return 0


def runtime_cli(action, session_id=None, root=None):
    """Report real OpenCode runtime capability and session evidence."""
    from pathlib import Path as _Path
    if action == "detect":
        info = detect_runtime(refresh=True)
        print(json.dumps(info.to_dict(), indent=2, ensure_ascii=False))
        return 0 if info.available else 2
    if action == "agents":
        agents = list_agents()
        print(json.dumps(agents, indent=2, ensure_ascii=False))
        return 0 if agents else 2
    if action == "models":
        models = list_models()
        print(json.dumps(models, indent=2, ensure_ascii=False))
        return 0 if models else 2
    if action == "verify":
        if not session_id:
            print("INVALID: --session-id is required", file=sys.stderr)
            return 1
        evidence = verify_session(session_id, _Path(root) if root else None)
        print(json.dumps(evidence, indent=2, ensure_ascii=False))
        return 0 if evidence.get("verified") else 2
    print(f"Unknown runtime action: {action}", file=sys.stderr)
    return 1


def main(argv=None):
    # Keep emitted JSON and diagnostics portable when the host console uses a
    # legacy encoding. Imports do not change the embedding application's streams.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("package", "registry", "digest", "scope"):
        command = commands.add_parser(name)
        command.add_argument("path")
        if name == "registry":
            command.add_argument("--migration-proposal", action="store_true",
                                help="emit a Schema 1 to 2 proposal as JSON; never write files")
    state_parser = commands.add_parser("state")
    state_parser.add_argument("path")
    state_parser.add_argument("--root", required=True)
    state_parser.add_argument("--gate", choices=("implement", "review", "advance"))
    migration_parser = commands.add_parser("migrate-state")
    migration_parser.add_argument("path")
    migration_parser.add_argument("--root", required=True)
    migration_parser.add_argument("--required-check", action="append", default=[], metavar="NAME")
    commands.add_parser("snapshot").add_argument("root")

    # New M2 Slice 1 commands (read-only unless explicitly noted)
    intake_parser = commands.add_parser("intake")
    intake_parser.add_argument("root", type=Path)
    intake_parser.add_argument("--project-id", type=str)

    arch_team_parser = commands.add_parser("arch-team")
    arch_team_parser.add_argument("root", type=Path)
    arch_team_parser.add_argument("action", choices=["decompose", "integrate"])

    research_parser = commands.add_parser("research")
    research_parser.add_argument("root", type=Path)
    research_parser.add_argument("task_id", type=str)
    research_parser.add_argument("action", choices=["execute", "status"])

    task_contracts_parser = commands.add_parser("task-contracts")
    task_contracts_parser.add_argument("root", type=Path)
    task_contracts_parser.add_argument("action", choices=["create-impl", "create-critic", "validate", "list"])
    task_contracts_parser.add_argument("--task-id", type=str)
    task_contracts_parser.add_argument("--role", type=str)
    task_contracts_parser.add_argument("--goal", type=str)
    task_contracts_parser.add_argument("--arch-version", type=str)
    task_contracts_parser.add_argument("--milestone", type=str)
    task_contracts_parser.add_argument("--review-target", type=str)
    task_contracts_parser.add_argument("--contract-refs", type=str, nargs="*")
    task_contracts_parser.add_argument("--input-paths", type=str, nargs="*")
    task_contracts_parser.add_argument("--dependencies", type=str, nargs="*")
    task_contracts_parser.add_argument("--allowed-actions", type=str, nargs="*")
    task_contracts_parser.add_argument("--acceptance", type=str, nargs="*")
    task_contracts_parser.add_argument("--required-checks", type=str, nargs="*")
    task_contracts_parser.add_argument("--skill-pins", type=str, nargs="*")
    task_contracts_parser.add_argument("--model-profile", type=str)
    task_contracts_parser.add_argument("--review-assignment", type=str)

    project_view_parser = commands.add_parser("project-view")
    project_view_parser.add_argument("root", type=Path)
    project_view_parser.add_argument("action", choices=["generate", "status"])
    project_view_parser.add_argument("--status", type=str, default="Entwurf")

    pair_exec_parser = commands.add_parser("pair-exec")
    pair_exec_parser.add_argument("root", type=Path)
    pair_exec_parser.add_argument("action", choices=["run-pair"])
    pair_exec_parser.add_argument("--impl-task-id", type=str, required=True)
    pair_exec_parser.add_argument("--critic-task-id", type=str)
    pair_exec_parser.add_argument("--max-rounds", type=int, default=2)

    integration_parser = commands.add_parser("integration")
    integration_parser.add_argument("root", type=Path)
    integration_parser.add_argument("action", choices=["run"])
    integration_parser.add_argument("--test-commands", type=str, nargs="*")

    lead_parser = commands.add_parser("lead")
    lead_parser.add_argument("root", type=Path)
    lead_parser.add_argument("action", choices=["run-lead"])
    lead_parser.add_argument("--lead-task-id", type=str, required=True)
    lead_parser.add_argument("--roster", type=str,
                             help="path to a JSON file with the agreed specialist roster")

    critic_parser = commands.add_parser("critic-report")
    critic_parser.add_argument("root", type=Path)
    critic_parser.add_argument("action", choices=["validate"])
    critic_parser.add_argument("--task-id", type=str, required=True)

    runtime_parser = commands.add_parser("runtime")
    runtime_parser.add_argument("action", choices=["detect", "agents", "models", "verify"])
    runtime_parser.add_argument("--session-id", type=str)
    runtime_parser.add_argument("--root", type=Path)

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
            if args.migration_proposal:
                print(json.dumps(migrate_registry(read_json(args.path, 1024 * 1024)),
                                 sort_keys=True, separators=(",", ":"), ensure_ascii=True))
            else:
                registry_file(args.path)
                print("OK registry")
        elif args.command == "package":
            package(args.path)
            print("OK package")
        elif args.command == "intake":
            return intake_cli(args.root, args.project_id)
        elif args.command == "arch-team":
            return arch_team_cli(args.root, args.action)
        elif args.command == "research":
            return research_cli(args.root, args.task_id, args.action)
        elif args.command == "task-contracts":
            kwargs = {k: v for k, v in vars(args).items() if k not in ("command", "action", "root")}
            return task_contracts_cli(args.root, args.action, **kwargs)
        elif args.command == "project-view":
            return project_view_cli(args.root, args.action, status=args.status)
        elif args.command == "pair-exec":
            kwargs = {k: v for k, v in vars(args).items() if k not in ("command", "action", "root")}
            return pair_execution_cli(args.root, args.action, **kwargs)
        elif args.command == "integration":
            kwargs = {k: v for k, v in vars(args).items() if k not in ("command", "action", "root")}
            return integration_cli(args.root, args.action, **kwargs)
        elif args.command == "runtime":
            return runtime_cli(args.action, session_id=args.session_id, root=args.root)
        elif args.command == "lead":
            kwargs = {k: v for k, v in vars(args).items() if k not in ("command", "action", "root")}
            return lead_execution_cli(args.root, args.action, **kwargs)
        elif args.command == "critic-report":
            return critic_report_cli(args.root, args.action, task_id=args.task_id)
        else:
            state(read_json(args.path, 64 * 1024), args.root, args.gate)
            print("OK state")
        return 0
    except (Invalid, OSError, UnicodeError, subprocess.SubprocessError, RecursionError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
