"""Read-only legacy registry and contained Schema 2 metadata processing."""
import re
import copy
import json
from pathlib import Path
from urllib.parse import urlparse
from .common import (Invalid, require, shape, string, strings, https, relative, iso_date,
                     hash_value, local_file, read_json, digest_bytes, canonical)


def _registry_v1(value):
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


def _identifier(value):
    require(isinstance(value, str) and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value),
            "registry identifier must be a lowercase hyphenated name")


def _source(entry):
    parsed = urlparse(entry['repository'])
    require(parsed.scheme == 'https' and parsed.netloc == 'github.com'
            and re.fullmatch(r'/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', parsed.path)
            and not parsed.path.endswith('.git'), 'Schema 2 requires a canonical GitHub repository URL')
    relative(entry['path'])
    relative(parsed.path.lstrip('/'))
    require('%' not in entry['path'] and entry['path'].split('/')[-1] != 'SKILL.md',
            'metadata.path must identify the skill directory, not an encoded path or manifest')
    return entry['repository'] + '/blob/' + entry['revision'] + '/'


def _pinned_reference(value, prefix):
    _record_https(value)
    require(value.startswith(prefix), 'evidence must bind the same repository/revision')
    relative(value[len(prefix):])
    require('%' not in value, 'encoded evidence paths are unsupported')


def _record_https(value):
    require(isinstance(value, str) and all(0x21 <= ord(char) <= 0x7e for char in value),
            'record references require ASCII URLs without whitespace or controls')
    try:
        https(value, 'record reference')
    except Invalid:
        raise
    except ValueError:
        raise Invalid('malformed record reference URL') from None


def registry_record(value):
    """Validate one metadata assertion; this never fetches or executes its source."""
    shape(value, 'schema_version metadata aliases verification runtime lifecycle', 'Schema 2 record')
    require(type(value['schema_version']) is int and value['schema_version'] == 2, 'record schema_version must be 2')
    try:
        canonical(value)
    except UnicodeError:
        raise Invalid('Schema 2 assertion strings must be UTF-8; preserve unsupported legacy values in migration drafts') from None
    entry = value['metadata']
    try:
        _registry_v1({'schema_version': 1, 'skills': [entry]})
    except Invalid:
        raise
    except ValueError:
        raise Invalid('malformed Schema 2 source or license URL') from None
    _identifier(entry['id'])
    _identifier(entry['name'])
    prefix = _source(entry)
    _pinned_reference(entry['license']['url'], prefix)
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.+-]*', entry['license']['spdx']), 'invalid license identifier')
    license_path = entry['license']['url'][len(prefix):]
    relative(license_path)
    require('%' not in license_path, 'encoded license paths are unsupported')
    strings(value['aliases'], 'aliases')
    aliases = value['aliases']
    require(len(set(aliases)) == len(aliases), 'duplicate alias')
    for alias in aliases:
        _identifier(alias)
        require(alias not in {entry['id'], entry['name']}, 'alias duplicates its own identity')
    verification = value['verification']
    shape(verification, 'status manifest_url manifest_sha256 license_status license_sha256 checked_at alias_evidence unknowns', 'verification')
    require(verification['status'] in ('unverified', 'source-verified'), 'invalid source verification status')
    _pinned_reference(verification['manifest_url'], prefix)
    require(verification['manifest_url'] == prefix + entry['path'] + '/SKILL.md', 'manifest reference does not bind canonical source/path/revision')
    strings(verification['unknowns'], 'verification.unknowns')
    if verification['status'] == 'source-verified':
        hash_value(verification['manifest_sha256'], 'manifest_sha256')
        iso_date(verification['checked_at'], 'checked_at')
        for item in entry['evidence']:
            _metadata_reference(item['reference'], entry)
    else:
        require(verification['manifest_sha256'] is None and verification['checked_at'] is None,
                'unverified source cannot claim a verified hash/date')
        require(bool(verification['unknowns']), 'unverified source requires explicit uncertainty')
    status = verification['license_status']
    require(status in ('verified', 'declared', 'unverified'), 'invalid license status')
    if status == 'verified':
        hash_value(verification['license_sha256'], 'license_sha256')
        require(verification['status'] == 'source-verified' and entry['license']['spdx'] != 'UNKNOWN',
                'verified license requires verified source and known license identity')
        require(Path(license_path).name.lower().startswith(('license', 'copying')), 'verified license needs a license-text reference')
    else:
        require(verification['license_sha256'] is None and bool(verification['unknowns']),
                'unverified/declared license requires null hash and explicit uncertainty')
        if status == 'declared':
            require(verification['status'] == 'source-verified' and entry['license']['spdx'] != 'UNKNOWN',
                    'declared license requires verified source declaration')
            require(entry['license']['url'] == verification['manifest_url'], 'declared license must cite its manifest declaration')
    proof = verification['alias_evidence']
    require(isinstance(proof, list), 'alias_evidence must be a list')
    proven = []
    for item in proof:
        shape(item, 'alias reference summary', 'alias evidence')
        _identifier(item['alias'])
        string(item['summary'], 'alias evidence summary')
        _pinned_reference(item['reference'], prefix)
        proven.append(item['alias'])
    require(len(set(proven)) == len(proven) and set(proven) == set(aliases), 'aliases need unique matching pinned evidence')
    require(not aliases or verification['status'] == 'source-verified', 'unverified sources cannot assert aliases')
    runtime = value['runtime']
    shape(runtime, 'requirements effects unknowns', 'runtime')
    for key in runtime:
        strings(runtime[key], 'runtime.' + key)
    require(bool(runtime['requirements'] or runtime['unknowns']), 'runtime requirements must be known or explicitly uncertain')
    require(bool(runtime['effects'] or runtime['unknowns']), 'runtime effects must be known or explicitly uncertain')
    life = value['lifecycle']
    shape(life, 'status reference reason', 'lifecycle')
    require(life['status'] in ('unknown', 'observed', 'catalog-deprecated', 'unavailable'), 'invalid lifecycle status')
    string(life['reason'], 'lifecycle.reason')
    if life['status'] == 'unknown':
        require(life['reference'] is None, 'unknown lifecycle must not claim supporting evidence')
    else:
        _pinned_reference(life['reference'], prefix)
    if entry['trust'] in ('reviewed', 'tested', 'approved'):
        require(verification['status'] == 'source-verified' and status == 'verified'
                and not runtime['unknowns'], 'stronger trust requires resolved source/license/runtime evidence')


def _metadata_reference(value, entry):
    """M1b supports pinned GitHub evidence; other legacy references stay in drafts."""
    _record_https(value)
    prefixes = [entry['repository'] + '/' + kind + '/' + entry['revision'] + '/'
                for kind in ('blob', 'tree')]
    require(any(value.startswith(prefix) for prefix in prefixes), 'metadata evidence must bind canonical repository and revision')
    prefix = next(p for p in prefixes if value.startswith(p))
    _pinned_reference(value, prefix)


def _records(index, values):
    shape(index, 'schema_version records', 'Schema 2 index')
    require(type(index['schema_version']) is int and index['schema_version'] == 2, 'index schema_version must be 2')
    require(isinstance(index['records'], list), 'records must be a list')
    require(len(index['records']) <= 256, 'Schema 2 index exceeds 256 records')
    require(len(index['records']) == len(values), 'index/record count mismatch')
    identifiers, identities, paths = set(), set(), set()
    for ref, value in zip(index['records'], values):
        shape(ref, 'id path', 'record reference')
        _identifier(ref['id'])
        require(ref['path'] == 'skills/' + ref['id'] + '.json', 'record path must match contained canonical ID')
        require(ref['path'] not in paths, 'duplicate record path')
        paths.add(ref['path'])
        registry_record(value)
        entry = value['metadata']
        require(ref['id'] == entry['id'], 'index/record ID mismatch')
        identity = (entry['repository'].lower(), entry['path'])
        require(identity not in identities, 'duplicate upstream identity')
        identities.add(identity)
        names = {entry['id'], entry['name'], *value['aliases']}
        require(not identifiers.intersection(names), 'registry ID/name/alias collision')
        identifiers.update(names)


def registry(value, root=None):
    """Schema 1 retains its original guarantees; Schema 2 indexes need an explicit root."""
    if isinstance(value, dict) and type(value.get('schema_version')) is int and value['schema_version'] == 2:
        if 'metadata' in value:
            return registry_record(value)
        shape(value, 'schema_version records', 'Schema 2 index')
        require(root is not None, 'Schema 2 index requires an explicit registry root')
        require(isinstance(value['records'], list), 'records must be a list')
        require(len(value['records']) <= 256, 'Schema 2 index exceeds 256 records')
        values = []
        total = 0
        for ref in value['records']:
            shape(ref, 'id path', 'record reference')
            _identifier(ref['id'])
            require(ref['path'] == 'skills/' + ref['id'] + '.json', 'record path must match contained canonical ID')
            values.append(read_json(local_file(Path(root).resolve(strict=True), ref['path']), 1024 * 1024))
            total += len(json.dumps(values[-1], sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii'))
            require(total <= 16 * 1024 * 1024, 'Schema 2 records exceed 16 MiB aggregate limit')
        return _records(value, values)
    return _registry_v1(value)


def registry_file(path):
    """Read only the supplied registry and its contained index references."""
    path = Path(path)
    value = read_json(path, 1024 * 1024)
    if isinstance(value, dict) and type(value.get('schema_version')) is int and value['schema_version'] == 2:
        root = path.parent.resolve(strict=True)
        local_file(root, path.name)
        return registry(value, root)
    return registry(value)


def migrate_registry(value):
    """Emit a proposal in memory; preserve exact legacy values, never write or grant trust."""
    try:
        _registry_v1(value)
    except Invalid:
        raise
    except ValueError:
        raise Invalid('malformed legacy URL in migration input') from None
    index = {'schema_version': 2, 'records': []}
    records, issues = [], []
    for original in value['skills']:
        entry = copy.deepcopy(original)
        record = {'schema_version': 2, 'metadata': entry, 'aliases': [],
                  'verification': {'status': 'unverified', 'manifest_url': entry['repository'] + '/blob/' + entry['revision'] + '/' + entry['path'] + '/SKILL.md',
                                   'manifest_sha256': None, 'license_status': 'unverified', 'license_sha256': None,
                                   'checked_at': None, 'alias_evidence': [],
                                   'unknowns': ['Migration copied legacy assertions without fetching or verifying manifest/license/aliases.']},
                  'runtime': {'requirements': copy.deepcopy(entry['compatibility']), 'effects': [],
                              'unknowns': ['Legacy metadata does not establish complete executable effects or dependency closure.']},
                  'lifecycle': {'status': 'unknown', 'reference': None, 'reason': 'Migration does not infer maintenance or lifecycle.'}}
        safe = isinstance(entry['id'], str) and re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', entry['id'])
        path = 'skills/' + entry['id'] + '.json' if safe else None
        index['records'].append({'id': entry['id'], 'path': path})
        records.append({'path': path, 'value': record})
    try:
        _records(index, [item['value'] for item in records])
    except Invalid as exc:
        issues.append(str(exc))
    try:
        source_bytes, source_encoding = canonical(value), 'canonical-utf8'
    except UnicodeError:
        source_bytes = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
        source_encoding = 'canonical-json-ascii'
    return {'proposal_version': 1, 'source_sha256': digest_bytes(source_bytes), 'source_encoding': source_encoding,
            'source': copy.deepcopy(value), 'index': index, 'records': records,
            'validation_issues': issues, 'ready_for_validation': not issues}
