import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const cwd = fileURLToPath(new URL('..', import.meta.url));
const fixture = String.raw`
import tempfile, json, io, tarfile
from pathlib import Path
from release import pack, verify, write_json, digest, REPOSITORY, WORKFLOW
from copy import deepcopy
with tempfile.TemporaryDirectory() as temp:
 root=Path(temp); dist=root/'dist'; dist.mkdir()
 for name in ('de/index.html','en/index.html','404.html'):
  path=dist/name; path.parent.mkdir(exist_ok=True); path.write_text('<h1>Fixture</h1>')
 source='a'*40
 tools={'node':'v24.22.0','python':'3.12','lighthouse':'13.5.0','chromium':'Chrome/test'}
 evidence={'source_sha':source,'local_performance':'passed','required_jobs':'passed'}
 out=root/'candidate'; m=pack(dist,out,source,123,1,tools,evidence)
 run={'id':123,'run_attempt':1,'repository':{'full_name':REPOSITORY},'head_repository':{'full_name':REPOSITORY},'path':WORKFLOW,'event':'push','status':'completed','conclusion':'success','head_sha':source}
 artifact={'id':456,'name':'website-candidate','expired':False,'workflow_run':{'id':123,'head_sha':source}}
 trusted={'run':run,'artifact':artifact}; trusted_path=root/'trusted.json'; archive=out/'site.tar.gz'; manifest=out/'manifest.json'; expected=m['archive_sha256']
 CASE
 write_json(trusted_path,trusted); write_json(manifest,m)
 try:
  verify(archive,manifest,trusted_path,source,expected,root/'extracted')
  accepted=True
 except (ValueError, KeyError, TypeError, OSError, tarfile.TarError): accepted=False
 assert accepted == EXPECTED, ('Unexpected acceptance', accepted)
 if accepted:
  assert (root/'extracted/de/index.html').read_text() == '<h1>Fixture</h1>'
  assert json.loads((root/'extracted/release.json').read_text())['source_sha']==source
 else: assert not (root/'extracted').exists(), 'Rejected archive wrote files'
`;
const cases = {
  'valid roundtrip writes only verified bytes': ['', true],
  'changed archive is rejected': ["archive.write_bytes(archive.read_bytes()+b'tampered')", false],
  'changed manifest inventory is rejected': ["m['files']['de/index.html']='0'*64", false],
  'wrong approved SHA is rejected': ["source='b'*40", false],
  'wrong repository is rejected': ["run['repository']['full_name']='attacker/fork'", false],
  'wrong workflow is rejected': ["run['path']='.github/workflows/other.yml'", false],
  'fork origin is rejected': ["run['head_repository']['full_name']='attacker/fork'", false],
  'PR origin is rejected': ["run['event']='pull_request'", false],
  'failed origin is rejected': ["run['conclusion']='failure'", false],
  'unfinished origin is rejected': ["run['status']='in_progress'", false],
  'mismatched run id is rejected': ["artifact['workflow_run']['id']=124", false],
  'invalid artifact id is rejected': ["artifact['id']=False", false],
  'expired artifact is rejected': ["artifact['expired']=True", false],
  'missing metadata is rejected': ["del trusted['artifact']", false],
  'malformed metadata is rejected': ["trusted['run']=[]", false],
  'missing evidence is rejected': ["m['evidence']={}", false],
  'missing tool version is rejected': ["del m['tools']['chromium']", false],
  'wrong artifact name is rejected': ["artifact['name']='diagnostics'", false],
};
for (const [name, [code, accepted]] of Object.entries(cases)) test(name, () => {
  const result = spawnSync('python', ['-c', fixture.replace(' CASE', code.split('\n').map(line => ' '+line).join('\n')).replace('EXPECTED', accepted ? 'True' : 'False')], { cwd, encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr || result.stdout);
});
for (const kind of ['traversal', 'absolute', 'backslash', 'symlink', 'duplicate', 'identity', 'casecollision', 'reserved', 'parentcollision']) test(`rejects ${kind} even with recomputed archive hash`, () => {
  const code = String.raw`
bad=root/'bad.tar.gz'
with tarfile.open(archive,'r:gz') as old, tarfile.open(bad,'w:gz') as new:
 for member in old:
  data=old.extractfile(member).read()
  if '${kind}'=='identity' and member.name=='release.json': data=b'{}'; member.size=len(data)
  new.addfile(member,io.BytesIO(data))
 extra=tarfile.TarInfo({'traversal':'../escape','absolute':'/escape','backslash':'..\\escape','casecollision':'DE/index.html','reserved':'CON','parentcollision':'de'}.get('${kind}','de/index.html'))
 if '${kind}'=='symlink': extra.type=tarfile.SYMTYPE; extra.linkname='/etc/passwd'
 if '${kind}'!='identity': new.addfile(extra,io.BytesIO(b''))
archive.write_bytes(bad.read_bytes()); expected=digest(archive.read_bytes()); m['archive_sha256']=expected
`;
  const result = spawnSync('python', ['-c', fixture.replace(' CASE', code.trim().split('\n').map(line => ' '+line).join('\n')).replace('EXPECTED', 'False')], { cwd, encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr || result.stdout);
});
