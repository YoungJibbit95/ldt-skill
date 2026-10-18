import { test, expect, chromium } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mkdir, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

const routes = ['', 'docs/', 'docs/install/', 'docs/guide/', 'docs/workflow/', 'docs/approvals/', 'docs/memory/', 'docs/checks/', 'docs/registry/', 'docs/limits/', 'demo/', 'built-with-littledevteam/'];

for (const locale of ['de', 'en']) {
  for (const width of [375, 768, 1440]) {
    test(`${locale}/${width}: every content route fits and preserves its translation`, async ({ page }) => {
      test.setTimeout(60000);
      await page.setViewportSize({ width, height: 1000 });
      for (const route of routes) {
        const response = await page.goto(`/ltd-skill/${locale}/${route}`);
        expect(response?.status(), route).toBe(200);
        await page.evaluate(() => document.fonts.ready);
        await expect(page.locator('html')).toHaveAttribute('lang', locale);
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), route).toBe(true);
        await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
        const counterpart = page.getByRole('link', { name: locale === 'de' ? 'Switch to English' : 'Zu Deutsch wechseln' });
        await expect(counterpart).toHaveAttribute('href', `/ltd-skill/${locale === 'de' ? 'en' : 'de'}/${route}`);
      }
    });
  }

  test(`${locale}: primary targets, workflow readability and search accessibility`, async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 1000 });
    await page.goto(`/ltd-skill/${locale}/`);
    for (const target of await page.locator('.hero-buttons a').all()) {
      const box = await target.boundingBox();
      expect(box?.height).toBeGreaterThanOrEqual(44);
      expect(box?.width).toBeGreaterThanOrEqual(44);
    }
    expect(await page.locator('.hero-intro').evaluate(el => parseFloat(getComputedStyle(el).fontSize))).toBeGreaterThanOrEqual(16);
    await page.goto(`/ltd-skill/${locale}/demo/`);
    for (const target of await page.locator('.language-link, .mobile-menu summary, .demo-navigation a, .demo-controls button:visible, [data-reset]').all()) {
      const box = await target.boundingBox();
      expect(box?.height).toBeGreaterThanOrEqual(44);
      expect(box?.width).toBeGreaterThanOrEqual(44);
    }
    for (const selector of ['.demo-scope', '.demo-navigation a', '.demo-meta', '.demo-artifact > p']) {
      for (const node of await page.locator(selector).all()) {
        expect(await node.evaluate(el => parseFloat(getComputedStyle(el).fontSize)), selector).toBeGreaterThanOrEqual(14);
      }
    }
    expect(await page.locator('.demo-stage-body').first().evaluate(el => parseFloat(getComputedStyle(el).fontSize))).toBeGreaterThanOrEqual(16);
    await page.locator('[data-reset]').focus();
    expect(await page.locator('[data-reset]').evaluate(el => getComputedStyle(el).outlineStyle)).not.toBe('none');
    await page.goto(`/ltd-skill/${locale}/docs/`);
    for (const target of await page.locator('[data-open-modal], .sl-menu-button').all()) {
      const box = await target.boundingBox();
      expect(box?.height).toBeGreaterThanOrEqual(44);
      expect(box?.width).toBeGreaterThanOrEqual(44);
    }
    await page.locator('[data-open-modal]').click();
    const audit = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
    expect(audit.violations.filter(v => ['serious', 'critical'].includes(v.impact ?? '')), JSON.stringify(audit.violations)).toEqual([]);
  });

  test(`${locale}: all content remains readable without JavaScript`, async ({ browser }) => {
    const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 375, height: 1000 } });
    const page = await context.newPage();
    for (const route of routes) {
      await page.goto(`/ltd-skill/${locale}/${route}`);
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
      expect((await page.locator('main').innerText()).length, route).toBeGreaterThan(150);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), route).toBe(true);
    }
    await page.goto(`/ltd-skill/${locale}/docs/install/`);
    for (const panel of await page.getByRole('tabpanel', { includeHidden: true }).all()) await expect(panel).toBeVisible();
    await context.close();
  });

  test(`${locale}: native Chromium zoom at 200 percent`, async ({}, testInfo) => {
    // Isolated, test-only extension calls Chromium's native tab zoom API.
    // It never touches the user's browser profile or installs an external package.
    const extension = testInfo.outputPath('zoom-extension');
    await mkdir(extension, { recursive: true });
    await writeFile(join(extension, 'manifest.json'), JSON.stringify({ manifest_version: 3, name: 'Local zoom acceptance fixture', version: '1.0', host_permissions: ['http://127.0.0.1/*'], background: { service_worker: 'background.js' } }));
    await writeFile(join(extension, 'background.js'), 'chrome.runtime.onInstalled.addListener(() => {});');
    const context = await chromium.launchPersistentContext('', { channel: 'chromium', headless: true, viewport: null, deviceScaleFactor: undefined, args: ['--window-size=1440,1000', `--disable-extensions-except=${extension}`, `--load-extension=${extension}`] });
    try {
      const worker = context.serviceWorkers()[0] ?? await context.waitForEvent('serviceworker');
      const page = context.pages()[0] ?? await context.newPage();
      await page.goto(`http://127.0.0.1:4321/ltd-skill/${locale}/`);
      const before = await page.evaluate(() => ({ width: innerWidth, dpr: devicePixelRatio }));
      const zoom = await worker.evaluate(async () => {
        const api = (globalThis as any).chrome;
        const [tab] = await api.tabs.query({ url: 'http://127.0.0.1/*' });
        await api.tabs.setZoom(tab.id, 2);
        return api.tabs.getZoom(tab.id);
      });
      expect(zoom).toBe(2);
      await expect.poll(() => page.evaluate(() => innerWidth)).toBeLessThan(before.width * 0.6);
      const after = await page.evaluate(() => ({ width: innerWidth, dpr: devicePixelRatio }));
      for (const route of ['', 'docs/install/', 'demo/']) {
        await page.goto(`http://127.0.0.1:4321/ltd-skill/${locale}/${route}`);
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), route).toBe(true);
        await page.locator('.mobile-menu summary').focus();
        await page.keyboard.press('Enter');
        await expect(page.locator('.mobile-menu nav')).toBeVisible();
      }
      await page.screenshot({ path: testInfo.outputPath('native-zoom.png'), animations: 'disabled' });
      await testInfo.attach('native-zoom-evidence', { body: JSON.stringify({ zoom, before, after, browser: context.browser()?.version() }), contentType: 'application/json' });
    } finally { await context.close(); }
  });

  test(`${locale}: 200-percent zoom reflow model remains usable`, async ({ browser }) => {
    // A 1440px display at 200% browser zoom has a 720 CSS-pixel layout viewport.
    // Record this as a reflow model, rather than a native-browser zoom command.
    const context = await browser.newContext({ viewport: { width: 720, height: 500 }, deviceScaleFactor: 2 });
    const page = await context.newPage();
    for (const route of ['', 'docs/install/', 'demo/']) {
      await page.goto(`/ltd-skill/${locale}/${route}`);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), route).toBe(true);
      await page.locator('.mobile-menu summary').focus();
      await page.keyboard.press('Enter');
      await expect(page.locator('.mobile-menu nav')).toBeVisible();
    }
    await context.close();
  });
}
