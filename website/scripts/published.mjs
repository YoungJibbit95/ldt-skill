// Explicitly opt-in: this script reads a deployed site and never publishes it.
import { chromium } from 'playwright';
import { expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { writeFile } from 'node:fs/promises';
import { createReportDirectory } from './report-directory.mjs';
import { assetPolicy } from './public-asset-policy.mjs';
import { join } from 'node:path';
import { parseArgs } from 'node:util';
const { values } = parseArgs({ options: { public: { type: 'boolean' }, sha: { type: 'string' }, output: { type: 'string' }, origin: { type: 'string', default: 'https://youngjibbit95.github.io' } } });
if (!values.public || !/^[a-f0-9]{40}$/.test(values.sha ?? '') || !values.output) throw new Error('Explicit --public, --sha and a new --output directory are required.');
if (values.origin !== 'https://youngjibbit95.github.io') throw new Error('Only the approved Pages origin may be checked.');
await createReportDirectory(values.output);
const base = `${values.origin}/ltd-skill/`;
const report = { schema: 1, source_sha: values.sha, origin: values.origin, started_at: new Date().toISOString(), attempts: [], routes: [], status: 'running' };
const save = () => writeFile(join(values.output, 'published.json'), JSON.stringify(report, null, 2) + '\n');
await save();
let browser;
try {
  // Retry only release propagation, for at most five minutes. Every attempt remains evidence.
  const deadline = Date.now() + 300000;
  let identityReady = false;
  do {
    try {
      const response = await fetch(`${base}release.json?verify=${Date.now()}`, { cache: 'no-store', signal: AbortSignal.timeout(Math.max(1, Math.min(10000, deadline - Date.now()))) });
      const identity = await response.json();
      identityReady = response.ok && identity.repository === 'YoungJibbit95/ltd-skill' && identity.source_sha === values.sha;
      report.attempts.push({ at: new Date().toISOString(), http: response.status, source_sha: identity.source_sha, matched: identityReady });
    } catch (error) { report.attempts.push({ at: new Date().toISOString(), error: String(error), matched: false }); }
    await save();
    if (!identityReady && Date.now() < deadline) await new Promise(resolve => setTimeout(resolve, Math.min(10000, deadline - Date.now())));
  } while (!identityReady && Date.now() < deadline);
  if (!identityReady) throw new Error('Release identity did not propagate within five minutes.');
  browser = await chromium.launch();
  const context = await browser.newContext({ permissions: ['clipboard-read', 'clipboard-write'] });
  const page = await context.newPage();
  const badAssets = [], pageErrors = [], fontAssets = new Set();
  report.asset_failures = badAssets;
  report.page_errors = pageErrors;
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('request', request => {
    const policy = assetPolicy(request.url(), request.resourceType(), base);
    if (policy.checked && !policy.allowed) badAssets.push({ url: request.url(), error: 'Asset is outside the approved origin and base path' });
  });
  page.on('requestfailed', request => {
    if (assetPolicy(request.url(), request.resourceType(), base).checked) badAssets.push({ url: request.url(), error: request.failure()?.errorText ?? 'Asset network request failed' });
  });
  page.on('response', response => {
    if (assetPolicy(response.url(), response.request().resourceType(), base).checked && response.status() >= 400) badAssets.push({ url: response.url(), status: response.status() });
    if (response.url().startsWith(base) && response.request().resourceType() === 'font' && response.ok()) fontAssets.add(response.url());
  });
  const root = await page.goto(base);
  expect(root.ok()).toBeTruthy();
  await expect(page).toHaveURL(`${base}de/`);
  for (const locale of ['de', 'en']) {
    for (const route of ['', 'docs/', 'docs/install/', 'docs/guide/', 'docs/workflow/', 'docs/approvals/', 'docs/memory/', 'docs/checks/', 'docs/registry/', 'docs/limits/', 'demo/', 'built-with-littledevteam/']) {
      const url = `${base}${locale}/${route}`;
      expect((await page.goto(url)).status(), url).toBe(200);
      expect((await page.reload()).status(), `reload ${url}`).toBe(200);
      await expect(page.locator('html')).toHaveAttribute('lang', locale);
      await expect(page.locator('link[rel="canonical"]')).toHaveAttribute('href', url);
      const other = locale === 'de' ? 'en' : 'de';
      await expect(page.locator(`link[rel="alternate"][hreflang="${other}"]`)).toHaveAttribute('href', `${base}${other}/${route}`);
      await page.getByRole('link', { name: locale === 'de' ? 'Switch to English' : 'Zu Deutsch wechseln', exact: true }).click();
      await expect(page).toHaveURL(`${base}${other}/${route}`);
      await page.waitForLoadState('load');
      await page.evaluate(() => document.fonts.ready);
      report.routes.push({ url, direct: 200, reload: 200, language_switch: true });
    }
    await page.goto(`${base}${locale}/docs/`);
    const opener = page.locator('button[data-open-modal]');
    await opener.focus(); await page.keyboard.press('Enter');
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    const search = dialog.getByRole('textbox', { name: locale === 'de' ? 'Suchen' : 'Search', exact: true });
    await search.fill(locale === 'de' ? 'Umfangsfingerabdruck' : 'scope fingerprint');
    const links = dialog.locator('.pagefind-ui__result-link');
    await expect(links.first()).toBeVisible();
    expect((await links.evaluateAll(nodes => nodes.map(node => node.getAttribute('href')))).every(href => href.includes(`/ltd-skill/${locale}/`))).toBeTruthy();
    await search.fill('zzqxnonexistent987654');
    await expect(dialog.locator('.pagefind-ui__message')).toContainText(locale === 'de' ? /keine|keinen/i : /no results/i);
    const searchAudit = await new AxeBuilder({ page }).analyze();
    expect(searchAudit.violations.filter(item => ['serious', 'critical'].includes(item.impact)), 'Search accessibility').toEqual([]);
    await page.keyboard.press('Escape'); await expect(opener).toBeFocused();
    await page.setViewportSize({ width: 375, height: 950 });
    await page.goto(`${base}${locale}/docs/install/`);
    const copy = page.locator('.expressive-code .copy button').first();
    await copy.focus(); await page.keyboard.press('Enter');
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toMatch(/git clone/);
    await page.goto(`${base}${locale}/demo/`);
    await page.locator('[data-stage-link="2"]').click(); await page.locator('[data-revise]').click();
    await page.locator('[data-stage-link="3"]').click();
    await page.locator('[data-approve]').focus(); await page.keyboard.press('Enter');
    await expect(page.locator('[data-stage="4"] h2')).toBeFocused();
    await page.locator('[data-reset]').click(); await expect(page.locator('[data-stage="0"]')).toBeVisible();
    await page.setViewportSize({ width: 375, height: 950 });
    await page.locator('.mobile-menu summary').focus(); await page.keyboard.press('Enter');
    await expect(page.locator('.mobile-menu nav')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
    await page.setViewportSize({ width: 1440, height: 950 });
    for (const route of ['', 'docs/install/', 'demo/']) {
      await page.goto(`${base}${locale}/${route}`);
      const audit = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
      expect(audit.violations.filter(item => ['serious', 'critical'].includes(item.impact)), route).toEqual([]);
    }
  }
  const nojs = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 375, height: 950 } });
  const inert = await nojs.newPage();
  for (const locale of ['de', 'en']) {
    await inert.goto(`${base}${locale}/demo/`);
    for (let step = 0; step < 8; step++) await expect(inert.locator(`[data-stage="${step}"]`)).toBeVisible();
    await inert.goto(`${base}${locale}/docs/install/`);
    for (const panel of await inert.getByRole('tabpanel', { includeHidden: true }).all()) await expect(panel).toBeVisible();
  }
  await nojs.close();
  expect((await fetch(`${base}favicon.svg`)).status).toBe(200);
  const unknown = await page.goto(`${base}unknown-release-check-${values.sha}/`);
  expect(unknown.status(), 'True HTTP 404').toBe(404);
  await expect(page).toHaveTitle('404 — LittleDevTeam');
  await expect(page.getByText('404 · OUTSIDE THE ORBIT', { exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Diese Seite liegt außerhalb unserer Umlaufbahn.', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Zur deutschen Startseite ↗', exact: true })).toHaveAttribute('href', '/ltd-skill/de/');
  await expect(page.getByRole('link', { name: 'Open English homepage ↗', exact: true })).toHaveAttribute('href', '/ltd-skill/en/');
  report.custom_404 = { http: unknown.status(), intended_content: true, both_home_links: true };
  expect(fontAssets.size, 'Locally served fonts loaded').toBeGreaterThan(0);
  expect(badAssets).toEqual([]); expect(pageErrors).toEqual([]);
  report.font_assets = [...fontAssets]; report.asset_failures = badAssets; report.status = 'passed';
  await context.close();
} catch (error) { report.status = 'failed'; report.error = String(error); }
finally { if (browser) await browser.close(); report.finished_at = new Date().toISOString(); await save(); }
console.log(JSON.stringify({ status: report.status, output: values.output, error: report.error }));
if (report.status !== 'passed') process.exitCode = 1;
