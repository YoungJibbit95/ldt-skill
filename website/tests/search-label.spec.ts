import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

for (const locale of ['de', 'en'] as const) {
  for (const width of [375, 768, 1440]) {
    test(`${locale}/${width}: search has a visible localized label and passes unfiltered Axe`, async ({ page }) => {
      test.setTimeout(60000);
      await page.setViewportSize({ width, height: 1000 });
      await page.goto(`/ltd-skill/${locale}/docs/`);
      const opener = page.locator('button[data-open-modal]');
      await expect(opener).toBeEnabled();
      await opener.focus();
      await page.keyboard.press('Enter');
      const dialog = page.getByRole('dialog');
      const name = locale === 'de' ? 'Suchen' : 'Search';
      const input = dialog.getByRole('textbox', { name, exact: true });
      const label = dialog.locator('label.search-input-label');
      await expect(label).toBeVisible();
      await expect(label).toHaveText(name);
      await expect(label).toHaveAttribute('for', await input.getAttribute('id') ?? '');
      expect(await input.evaluate(node => [...((node as HTMLInputElement).labels ?? [])].map(item => item.textContent))).toEqual([name]);
      await label.click();
      await expect(input).toBeFocused();
      const labelBox = await label.boundingBox();
      const inputBox = await input.boundingBox();
      expect(labelBox?.height).toBeGreaterThan(0);
      expect(labelBox!.y + labelBox!.height).toBeLessThanOrEqual(inputBox!.y);
      const assertAccessible = async () => {
        const audit = await new AxeBuilder({ page }).analyze();
        expect(audit.violations.filter(item => ['serious', 'critical'].includes(item.impact ?? '')), JSON.stringify(audit.violations, null, 2)).toEqual([]);
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
        expect(await dialog.evaluate(node => node.scrollWidth <= node.clientWidth + 1)).toBe(true);
      };
      await assertAccessible();
      await input.fill(locale === 'de' ? 'Umfangsfingerabdruck' : 'scope fingerprint');
      await expect(dialog.locator('.pagefind-ui__result-link').first()).toBeVisible();
      await expect(label).toBeVisible();
      await input.fill('zzqxnonexistent987654');
      await expect(dialog.locator('.pagefind-ui__message')).toContainText(locale === 'de' ? /keine|keinen/i : /no results/i);
      await assertAccessible();
      await page.keyboard.press('Escape');
      await expect(dialog).not.toBeVisible();
      await expect(opener).toBeFocused();
      await page.keyboard.press('Enter');
      await expect(input).toBeFocused();
      await expect(label).toBeVisible();
      await expect(dialog.locator('label.search-input-label')).toHaveCount(1);
    });
  }
}
