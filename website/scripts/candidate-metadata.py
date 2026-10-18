"""Fetch separately trusted GitHub metadata and download an inert candidate zip."""
import argparse
import json
import os
from pathlib import Path
import urllib.request
from urllib.parse import urlparse
import zipfile
import io
from release import REPOSITORY, WORKFLOW, require, positive, sha, write_json

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--run', type=int, required=True)
p.add_argument('--artifact', type=int, required=True)
p.add_argument('--sha', required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
positive(a.run)
positive(a.artifact)
sha(a.sha)
require(not a.output.exists(), 'Download directory must not exist')

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        require(urlparse(newurl).scheme == 'https', 'Insecure API redirect')
        redirected = super().redirect_request(request, fp, code, message, headers, newurl)
        if urlparse(request.full_url).netloc != urlparse(newurl).netloc:
            redirected.remove_header('Authorization')
        return redirected

opener = urllib.request.build_opener(SafeRedirect())

def api(path, raw=False):
    request = urllib.request.Request('https://api.github.com/repos/' + REPOSITORY + path,
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'})
    with opener.open(request, timeout=60) as response:
        body = response.read(300_000_001)
    require(len(body) <= 300_000_000, 'API response exceeds size limit')
    return body if raw else json.loads(body)

run = api(f'/actions/runs/{a.run}')
artifact = api(f'/actions/artifacts/{a.artifact}')
require(run['id'] == a.run and artifact['id'] == a.artifact, 'API identifier mismatch')
require(run['repository']['full_name'] == run['head_repository']['full_name'] == REPOSITORY, 'Wrong repository/fork')
require(run['path'] == WORKFLOW and run['event'] in ('push', 'workflow_dispatch'), 'Wrong workflow/event')
require(run['head_sha'] == a.sha and run['status'] == 'completed' and run['conclusion'] == 'success', 'Origin run has not succeeded for this revision')
require(artifact['name'] == 'website-candidate' and artifact['expired'] is False, 'Invalid or expired artifact')
require(artifact['workflow_run']['id'] == a.run and artifact['workflow_run']['head_sha'] == a.sha, 'Artifact belongs to another run/revision')
# A deployment may promote only source already reachable from main.
comparison = api(f'/compare/{a.sha}...main')
require(comparison['status'] in ('ahead', 'identical'), 'Approved SHA is not reachable from main')
body = api(f'/actions/artifacts/{a.artifact}/zip', raw=True)
with zipfile.ZipFile(io.BytesIO(body)) as archive:
    entries = archive.infolist()
    require(len(entries) == 2 and {entry.filename for entry in entries} == {'site.tar.gz', 'manifest.json'}, 'Unexpected artifact zip contents')
    require(all(not entry.is_dir() and entry.file_size < 250_000_000 and ((entry.external_attr >> 16) & 0o170000) != 0o120000 for entry in entries), 'Unsafe artifact zip')
    a.output.mkdir(parents=True)
    for entry in entries:
        (a.output / entry.filename).write_bytes(archive.read(entry))
write_json(a.output / 'trusted.json', {'run': run, 'artifact': artifact})
print(json.dumps({'run_id': a.run, 'artifact_id': a.artifact, 'expires_at': artifact['expires_at'], 'download_verified': True}))
