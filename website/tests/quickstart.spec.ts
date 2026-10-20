import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import prompts from '../src/data/quickstart.json' with { type: 'json' };

for (const locale of ['de', 'en'] as const) {
  for (const width of [320, 375, 768, 1440]) {
    test(`${locale}/${width}: shared Quickstart fits every entry and copies with keyboard`, async ({ page, context }) => {
      await context.grantPermissions(['clipboard-read', 'clipboard-write']);
      await page.setViewportSize({ width, height: 1000 });
      for (const route of ['', 'docs/', 'docs/guide/', 'docs/install/']) {
        await page.goto(`/ldt-skill/${locale}/${route}`);
        const card = page.locator('[data-quickstart]');
        await expect(card.locator('[data-prompt]')).toHaveText(prompts[locale]);
        await expect(card).toContainText(locale === 'de' ? 'Noch kein stabiles Release' : 'No stable release yet');
        await expect(card.getByRole('link').last()).toHaveAttribute('href', `/ldt-skill/${locale}/docs/install/`);
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), route).toBe(true);
        expect(await card.evaluate(el => el.scrollWidth <= el.clientWidth + 1), route).toBe(true);
        const button = card.getByRole('button');
        await button.focus();
        await expect(button).toBeFocused();
        expect(await button.evaluate(el => getComputedStyle(el).outlineStyle)).not.toBe('none');
        await page.keyboard.press('Enter');
        await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe(prompts[locale]);
        await expect(card.getByRole('status')).toHaveText(locale === 'de' ? 'Prompt kopiert.' : 'Prompt copied.');
        await expect(button).toBeFocused();
      }
    });
  }

  test(`${locale}: clipboard denial reports a useful failure and can retry`, async ({ page }) => {
    await page.addInitScript(() => {
      let calls = 0;
      Object.defineProperty(navigator, 'clipboard', { value: { writeText: async () => {
        if (calls++ === 0) throw new Error('Clipboard permission denied');
      } } });
    });
    await page.goto(`/ldt-skill/${locale}/docs/guide/`);
    const card = page.locator('[data-quickstart]');
    await card.getByRole('button').click();
    await expect(card.getByRole('status')).toContainText(locale === 'de' ? 'manuell' : 'manually');
    await expect(card.getByRole('status')).not.toContainText(locale === 'de' ? 'kopiert.' : 'copied.');
    await card.getByRole('button').click();
    await expect(card.getByRole('status')).toHaveText(locale === 'de' ? 'Prompt kopiert.' : 'Prompt copied.');
    const audit = await new AxeBuilder({ page }).include('[data-quickstart]').withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
    expect(audit.violations).toEqual([]);
  });

  test(`${locale}: no-JavaScript Quickstart stays selectable with manual guidance`, async ({ browser }) => {
    const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 320, height: 900 } });
    const page = await context.newPage();
    await page.goto(`/ldt-skill/${locale}/docs/`);
    const card = page.locator('[data-quickstart]');
    await expect(card.locator('[data-prompt]')).toHaveText(prompts[locale]);
    await expect(card.getByRole('button')).toBeDisabled();
    await expect(card.locator('[data-manual]')).toBeVisible();
    await expect(card.locator('[data-manual]')).toContainText(locale === 'de' ? 'manuell' : 'manually');
    await context.close();
  });
}
