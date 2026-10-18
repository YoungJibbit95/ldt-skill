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
        else:
            state(read_json(args.path, 64 * 1024), args.root, args.gate)
            print("OK state")
        return 0
    except (Invalid, OSError, UnicodeError, subprocess.SubprocessError, RecursionError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
