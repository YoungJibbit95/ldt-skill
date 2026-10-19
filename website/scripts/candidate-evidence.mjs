import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
const root = process.argv[2];
if (!root || !/^[a-f0-9]{40}$/.test(process.env.GITHUB_SHA ?? '')) throw new Error('Supply build directory and GITHUB_SHA.');
const summary = JSON.parse(await readFile(join(root, 'reports/performance/summary.json'), 'utf8'));
const needs = JSON.parse(process.env.REQUIRED_JOBS ?? '{}');
if (Object.keys(needs).sort().join(',') !== 'installation,skill,website' || Object.values(needs).some(job => job.result !== 'success')) throw new Error('Every required same-run job must have succeeded.');
if (summary.source_sha !== process.env.GITHUB_SHA || summary.mode !== 'local' || summary.status !== 'passed' || summary.results.length !== 12 || summary.medians.length !== 4 || summary.medians.some(item => !item.passed || item.median < 90)) throw new Error('Incomplete same-revision local performance evidence.');
const expectedRoutes = ['de/', 'en/', 'de/docs/install/', 'en/docs/install/'];
for (const route of expectedRoutes) {
  const results = summary.results.filter(item => item.url === `http://127.0.0.1:4321/ldt-skill/${route}`);
  if (results.map(item => item.run).sort().join(',') !== '1,2,3') throw new Error('Each approved URL requires exactly three distinct measurements.');
  const median = results.map(item => item.score).sort((a, b) => a - b)[1];
  if (!results.every(item => typeof item.score === 'number' && item.score >= 0 && item.score <= 100) || median < 90) throw new Error('Actual measurement median fails the approved policy.');
}
for (const result of summary.results) {
  for (const key of ['html', 'json']) {
    if (!/^[a-z0-9-]+\.(html|json)$/.test(result[key])) throw new Error('Unsafe report name.');
    const bytes = await readFile(join(root, 'reports/performance', result[key]));
    if (!bytes.length) throw new Error('Empty measurement report.');
  }
  const lhr = JSON.parse(await readFile(join(root, 'reports/performance', result.json), 'utf8'));
  if (lhr.lighthouseVersion !== '13.5.0' || lhr.categories.performance.score * 100 !== result.score || lhr.requestedUrl !== result.url) throw new Error('Measurement report differs from summary.');
}
const python = spawnSync('python', ['--version'], { encoding: 'utf8' });
if (python.status !== 0) throw new Error(python.stderr);
await writeFile(join(root, 'tools.json'), JSON.stringify({ ...summary.tools, python: python.stdout.trim() }, null, 2));
await writeFile(join(root, 'evidence.json'), JSON.stringify({ source_sha: process.env.GITHUB_SHA, local_performance: 'passed', required_jobs: 'passed',
  website: 'Production build, source/content parity, links, browser tests and contract tests', installation: 'Windows, macOS, Linux',
  skill: 'Linux/Windows, Python 3.10/3.12 package, both registries and regression suite',
  run_url: `https://github.com/${process.env.GITHUB_REPOSITORY}/actions/runs/${process.env.GITHUB_RUN_ID}`,
  public_checks: 'not_run', public_performance: 'not_run', independent_review: 'not_attested_by_ci; separate reviewer evidence required' }, null, 2));
