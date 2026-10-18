"""Reusable read-only validation API; importing it performs no validation or stream changes.

The validate.py facade owns argument parsing and console output. Modules here
contain the single implementation of the existing validation and gate rules.
"""
from .common import (
    Invalid, require, shape, string, strings, digest_bytes, canonical, hash_value,
    unique_object, read_json, relative, path_text, local_file, digest_file,
    iso_date, timestamp, https, HEX,
)
from .snapshots import (git, file_metadata, snapshot, MANAGED, WALK_IGNORED)
from .approvals import (scope_fields, scope, approval)
from .state import (artifact, state, migrate_state, PHASES)
from .registry import registry, registry_file, registry_record, migrate_registry
from .package import package

__all__ = [
    'Invalid', 'require', 'shape', 'string', 'strings', 'digest_bytes', 'canonical',
    'hash_value', 'unique_object', 'read_json', 'relative', 'path_text', 'local_file',
    'digest_file', 'iso_date', 'timestamp', 'https', 'HEX', 'git', 'file_metadata',
    'snapshot', 'MANAGED', 'WALK_IGNORED', 'scope_fields', 'scope', 'approval',
    'artifact', 'state', 'migrate_state', 'PHASES', 'registry', 'package',
    'registry_file', 'registry_record', 'migrate_registry',
]
