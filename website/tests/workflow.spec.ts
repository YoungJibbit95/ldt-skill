import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

for (const locale of ['de', 'en'] as const) {
  for (const width of [375, 1440]) {
    test(`${locale}/${width}: approval, revision, invalidation and reset`, async ({ page }) => {
      await page.setViewportSize({ width, height: 950 });
      const errors: string[] = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(`/ltd-skill/${locale}/demo/`);
      const demo = page.locator('ldt-demo');
      await expect(demo).toHaveAttribute('data-enhanced', '');
      await expect(demo.locator('[data-stage-link]')).toHaveCount(8);
      await expect(demo.locator('[data-stage="0"]')).toBeVisible();
      await demo.locator('[data-stage-link="4"]').click();
      await expect(demo.locator('[data-feedback]')).toContainText(locale === 'de' ? 'brauchst du zuerst' : 'need demo approval');
      await expect(demo.locator('[data-stage="0"]')).toBeVisible();
      await demo.locator('[data-stage-link="2"]').click();
      await demo.getByRole('button', { name: locale === 'de' ? 'Vorschlag überarbeiten' : 'Revise proposal' }).click();
      await expect(demo.locator('[data-revision]')).toContainText('2');
      await expect(demo.locator('[data-stage="2"]')).toContainText(locale === 'de' ? 'Installation im ersten Meilenstein' : 'installation in the first milestone');
      await demo.locator('[data-stage-link="3"]').click();
      await demo.getByRole('button', { name: locale === 'de' ? 'Demo-Freigabe erteilen' : 'Grant demo approval' }).focus();
      await page.keyboard.press('Enter');
      await expect(demo.locator('[data-stage="4"]')).toBeVisible();
      await expect(demo.locator('[data-stage="4"] h2')).toBeFocused();
      for (const stage of [5, 6, 7]) {
        await demo.locator('[data-next]').click();
        await expect(demo.locator(`[data-stage="${stage}"]`)).toBeVisible();
      }
      await expect(demo.locator('[data-next]')).toBeDisabled();
      await demo.locator('[data-stage-link="2"]').click();
      await demo.locator('[data-revise]').click();
      await demo.locator('[data-stage-link="4"]').click();
      await expect(demo.locator('[data-stage="2"]')).toBeVisible();
      await expect(demo.locator('[data-approval]')).toHaveText(locale === 'de' ? 'Freigabe offen' : 'Approval pending');
      await demo.getByRole('button', { name: locale === 'de' ? 'Zurücksetzen' : 'Reset' }).click();
      await expect(demo.locator('[data-stage="0"]')).toBeVisible();
      await expect(demo.locator('[data-revision]')).toContainText('1');
      await expect(demo.locator('[data-previous]')).toBeDisabled();
      await page.getByRole('link', { name: locale === 'de' ? 'Switch to English' : 'Zu Deutsch wechseln' }).click();
      await expect(page).toHaveURL(new RegExp(`/ltd-skill/${locale === 'de' ? 'en' : 'de'}/demo/$`));
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
      expect(errors).toEqual([]);
    });
  }

  test(`${locale}: localized search, empty results and keyboard return`, async ({ page }) => {
    await page.goto(`/ltd-skill/${locale}/docs/`);
    const open = page.locator('button[data-open-modal]');
    await open.focus();
    await page.keyboard.press('Enter');
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    const search = dialog.getByRole('textbox', { name: locale === 'de' ? 'Suchen' : 'Search', exact: true });
    await search.fill(locale === 'de' ? 'Umfangsfingerabdruck' : 'scope fingerprint');
    const results = dialog.locator('.pagefind-ui__result-link');
    await expect(results.first()).toBeVisible();
    const hrefs = await results.evaluateAll(nodes => nodes.map(node => node.getAttribute('href')));
    expect(hrefs.every(href => href?.includes(`/ltd-skill/${locale}/`))).toBe(true);
    await search.fill('zzqxnonexistent987654');
    await expect(dialog.locator('.pagefind-ui__message')).toContainText(locale === 'de' ? /keine|keinen/i : /no results/i);
    await page.keyboard.press('Escape');
    await expect(dialog).not.toBeVisible();
    await expect(open).toBeFocused();
  });

  test(`${locale}: revised demo remains accessible`, async ({ page }) => {
    await page.goto(`/ltd-skill/${locale}/demo/`);
    await page.locator('[data-stage-link="2"]').click();
    await page.locator('[data-revise]').click();
    const audit = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
    expect(audit.violations.filter(v => ['serious', 'critical'].includes(v.impact ?? '')), JSON.stringify(audit.violations)).toEqual([]);
  });
}

test('all demo steps and platform instructions remain readable without JavaScript', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 375, height: 950 } });
  const page = await context.newPage();
  await page.goto('/ltd-skill/en/demo/');
  for (const stage of [0, 1, 2, 3, 4, 5, 6, 7]) await expect(page.locator(`[data-stage="${stage}"]`)).toBeVisible();
  await expect(page.locator('[data-next]')).not.toBeVisible();
  await page.goto('/ltd-skill/en/docs/install/');
  for (const panel of await page.getByRole('tabpanel', { includeHidden: true }).all()) await expect(panel).toBeVisible();
  await context.close();
});
