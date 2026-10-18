import lighthouse from 'lighthouse';
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { createServer } from 'node:net';
import { mkdtemp, writeFile, readFile, rm } from 'node:fs/promises';
import { createReportDirectory } from './report-directory.mjs';
import { tmpdir, platform, release, cpus } from 'node:os';
import { join, resolve, relative, isAbsolute, basename, sep } from 'node:path';
import { parseArgs } from 'node:util';

const { values } = parseArgs({ options: {
  origin: { type: 'string', default: 'http://127.0.0.1:4321' },
  output: { type: 'string' }, sha: { type: 'string' }, public: { type: 'boolean', default: false },
} });
if (!values.output || !/^[a-f0-9]{40}$/.test(values.sha ?? '')) throw new Error('Supply --output (new directory) and --sha (full revision).');
const origin = new URL(values.origin);
if (origin.pathname !== '/' || origin.search || origin.hash || origin.username || origin.password) throw new Error('Supply an origin without a path or credentials.');
if (values.public ? origin.origin !== 'https://youngjibbit95.github.io' : origin.origin !== 'http://127.0.0.1:4321') throw new Error('Origin is outside the approved local/public measurement policy.');
const lighthouseVersion = JSON.parse(await readFile(new URL('../node_modules/lighthouse/package.json', import.meta.url), 'utf8')).version;
if (lighthouseVersion !== '13.5.0') throw new Error('The approved Lighthouse version is exactly 13.5.0.');
await createReportDirectory(values.output);
const summary = { schema: 1, source_sha: values.sha, mode: values.public ? 'public' : 'local', origin: origin.origin,
  started_at: new Date().toISOString(), policy: '3 serial fresh-profile mobile runs per URL; median >= 90; no selected retries',
  tools: { node: process.version, lighthouse: lighthouseVersion, chromium: null },
  runner: { platform: platform(), release: release(), cpu: cpus()[0]?.model, ci: process.env.GITHUB_ACTIONS === 'true', run_id: process.env.GITHUB_RUN_ID ?? null }, results: [], status: 'running' };
const save = () => writeFile(join(values.output, 'summary.json'), JSON.stringify(summary, null, 2) + '\n');
await save();
async function freePort() {
  const server = createServer();
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const port = server.address().port;
  await new Promise(resolve => server.close(resolve));
  return port;
}
try {
  if (values.public) {
    const identity = await (await fetch(`${origin.origin}/ltd-skill/release.json`, { cache: 'no-store' })).json();
    if (identity.source_sha !== values.sha) throw new Error('Public identity differs from the approved source SHA.');
  }
  for (const route of ['de/', 'en/', 'de/docs/install/', 'en/docs/install/']) {
    const scores = [];
    for (let run = 1; run <= 3; run++) {
      const profile = await mkdtemp(join(tmpdir(), 'ldt-lighthouse-'));
      const port = await freePort();
      const chrome = spawn(chromium.executablePath(), ['--headless', '--no-sandbox', '--disable-dev-shm-usage', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' });
      const closed = new Promise(resolveClosed => { chrome.once('close', resolveClosed); chrome.once('error', resolveClosed); });
      try {
        let ready = false;
        for (let attempt = 0; attempt < 100; attempt++) {
          try {
            const version = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json();
            summary.tools.chromium = version.Browser;
            ready = true; break;
          } catch { await new Promise(resolve => setTimeout(resolve, 100)); }
        }
        if (!ready) throw new Error('Chromium did not open a debugging port.');
        const url = `${origin.origin}/ltd-skill/${route}`;
        const result = await lighthouse(url, { port, output: ['html', 'json'], onlyCategories: ['performance'], formFactor: 'mobile', throttlingMethod: 'simulate', logLevel: 'error', disableStorageReset: false });
        if (!result) throw new Error('No Lighthouse result');
        const file = `${route.replaceAll('/', '-')}run-${run}`;
        await writeFile(join(values.output, `${file}.html`), result.report[0]);
        await writeFile(join(values.output, `${file}.json`), result.report[1]);
        const score = result.lhr.categories.performance?.score == null ? null : result.lhr.categories.performance.score * 100;
        summary.results.push({ url, run, score, runtime_error: result.lhr.runtimeError, html: `${file}.html`, json: `${file}.json`, lighthouse_version: result.lhr.lighthouseVersion, fetch_time: result.lhr.fetchTime, config: result.lhr.configSettings });
        await save();
        if (result.lhr.runtimeError || score === null) throw new Error(JSON.stringify(result.lhr.runtimeError ?? 'No performance score'));
        if (result.lhr.lighthouseVersion !== lighthouseVersion) throw new Error('Measured Lighthouse version differs from the locked tool.');
        scores.push(score);
      } finally {
        if (chrome.exitCode === null && chrome.signalCode === null) chrome.kill();
        await closed;
        const resolvedProfile = resolve(profile), tempRoot = resolve(tmpdir());
        const inside = relative(tempRoot, resolvedProfile);
        if (!inside || inside === '..' || inside.startsWith(`..${sep}`) || isAbsolute(inside) || !basename(resolvedProfile).startsWith('ldt-lighthouse-')) throw new Error('Refusing unsafe browser profile cleanup.');
        await rm(resolvedProfile, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 });
      }
    }
    const median = [...scores].sort((a, b) => a - b)[1];
    (summary.medians ??= []).push({ route, scores, median, passed: median >= 90 });
  }
  summary.status = summary.medians.every(item => item.passed) ? 'passed' : 'failed';
} catch (error) { summary.status = 'failed'; summary.error = String(error); }
summary.finished_at = new Date().toISOString();
await save();
console.log(JSON.stringify({ status: summary.status, medians: summary.medians, output: values.output }));
if (summary.status !== 'passed') process.exitCode = 1;
