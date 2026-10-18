import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { createReportDirectory } from '../report-directory.mjs';

test('fresh nested report output works, and an existing series remains intact', async () => {
  const sandbox = await mkdtemp(join(tmpdir(), 'ldt-report-test-'));
  const target = join(sandbox, 'new-reports', 'performance');
  await createReportDirectory(target);
  const report = join(target, 'evidence.json');
  await writeFile(report, '{"score":42}');
  await assert.rejects(createReportDirectory(target), { code: 'EEXIST' });
  assert.equal(await readFile(report, 'utf8'), '{"score":42}');
  // Small inert fixtures remain in the OS temporary directory; no recursive deletion.
});
