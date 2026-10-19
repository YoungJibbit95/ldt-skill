import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

for (const locale of ['de', 'en'] as const) {
  for (const width of [375, 768, 1440]) {
    test(`${locale} at ${width}px: entry, layout, language and navigation`, async ({ page, context }) => {
      await context.grantPermissions(['clipboard-read', 'clipboard-write']);
      await page.setViewportSize({ width, height: 1000 });
      const errors: string[] = [];
      page.on('pageerror', error => errors.push(error.message));
      const response = await page.goto(`/ldt-skill/${locale}/`);
      expect(response?.status()).toBe(200);
      await expect(page.locator('html')).toHaveAttribute('lang', locale);
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
      await page.evaluate(() => document.fonts.ready);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
      await page.getByRole('link', { name: locale === 'de' ? 'Switch to English' : 'Zu Deutsch wechseln' }).click();
      await expect(page).toHaveURL(new RegExp(`/ldt-skill/${locale === 'de' ? 'en' : 'de'}/$`));
      await page.goto(`/ldt-skill/${locale}/`);
      if (width <= 860) {
        await page.locator('.mobile-menu summary').focus();
        await page.keyboard.press('Enter');
        await expect(page.locator('.mobile-menu')).toHaveAttribute('open', '');
        await page.locator('.mobile-menu nav').getByRole('link', { name: locale === 'de' ? 'Dokumentation' : 'Documentation', exact: true }).click();
      } else await page.locator('.desktop-nav').getByRole('link', { name: locale === 'de' ? 'Dokumentation' : 'Documentation', exact: true }).click();
      await expect(page).toHaveURL(new RegExp(`/ldt-skill/${locale}/docs/$`));
      if (width < 800) {
        await page.locator('.sl-menu-button').focus();
        await page.keyboard.press('Enter');
        await expect(page.locator('#starlight__sidebar')).toBeVisible();
        await page.locator('#starlight__sidebar').getByRole('link', { name: 'Installation', exact: true }).click();
        await expect(page).toHaveURL(new RegExp(`/ldt-skill/${locale}/docs/install/$`));
      }
      await page.goto(`/ldt-skill/${locale}/docs/install/`);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
      const firstCodeBlock = page.locator('.expressive-code:visible').first();
      const expectedCode = (await firstCodeBlock.locator('pre code .ec-line .code').allTextContents()).join('\n').replace(/\r\n/g, '\n');
      expect(expectedCode.trim(), 'The first copied block contains visible code').not.toBe('');
      const firstCopy = firstCodeBlock.locator('.copy button');
      await page.evaluate(() => navigator.clipboard.writeText(''));
      await firstCopy.focus();
      await expect(firstCopy).toBeFocused();
      await page.keyboard.press('Enter');
      await expect.poll(async () => (await page.evaluate(() => navigator.clipboard.readText())).replace(/\r\n/g, '\n')).toBe(expectedCode);
      const bashTab = page.getByRole('tab', { name: 'macOS / Linux · Bash' }).first();
      await bashTab.click();
      await expect(bashTab).toHaveAttribute('aria-selected', 'true');
      const activePanel = page.getByRole('tabpanel').filter({ hasText: 'git clone' });
      await expect(activePanel).toBeVisible();
      const copy = activePanel.getByRole('button', { name: /copy|kopieren/i });
      await expect(copy).toBeVisible();
      await copy.focus();
      await expect(copy).toBeFocused();
      await page.keyboard.press('Enter');
      await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toContain('git clone https://github.com/YoungJibbit95/ldt-skill.git');
      await page.getByRole('link', { name: locale === 'de' ? 'Switch to English' : 'Zu Deutsch wechseln' }).click();
      await expect(page).toHaveURL(new RegExp(`/ldt-skill/${locale === 'de' ? 'en' : 'de'}/docs/install/$`));
      expect(errors).toEqual([]);
    });
  }

  test(`${locale}: no serious/critical accessibility violations`, async ({ page }) => {
    test.setTimeout(90000);
    await page.setViewportSize({ width: 1440, height: 1000 });
    for (const route of ['', 'docs/', 'docs/install/', 'docs/guide/', 'docs/workflow/', 'docs/approvals/', 'docs/memory/', 'docs/checks/', 'docs/registry/', 'docs/limits/', 'demo/', 'built-with-littledevteam/']) {
      await page.goto(`/ldt-skill/${locale}/${route}`);
      const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
      expect(result.violations.filter(v => ['serious', 'critical'].includes(v.impact ?? '')), JSON.stringify(result.violations, null, 2)).toEqual([]);
    }
  });
}

test('root points to German, and entry remains usable without JavaScript', async ({ browser, request }) => {
  const root = await request.get('/ldt-skill/');
  expect(await root.text()).toContain('/ldt-skill/de/');
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 375, height: 900 } });
  const page = await context.newPage();
  await page.goto('/ldt-skill/en/');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await page.locator('.mobile-menu summary').click();
  await page.locator('.mobile-menu nav').getByRole('link', { name: 'Guide', exact: true }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Your first task');
  await expect(page.getByRole('heading', { name: '1. Describe the outcome', exact: true })).toBeVisible();
  await context.close();
});

test('reduced motion disables ambient nebula animation', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/ldt-skill/de/');
  expect(await page.locator('.nebula').evaluate(node => getComputedStyle(node).animationName)).toBe('none');
});
