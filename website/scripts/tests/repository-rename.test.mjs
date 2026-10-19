import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const read = path => readFile(new URL(path, import.meta.url), 'utf8');

test('Pages base, release identity, public checks and browser tests use renamed repository', async () => {
  const [astro, site, release, published, linkChecker, playwright] = await Promise.all([
    read('../../astro.config.mjs'),
    read('../../src/lib/site.ts'),
    read('../release.py'),
    read('../published.mjs'),
    read('../check-links.mjs'),
    read('../../playwright.config.ts'),
  ]);
  assert.match(astro, /base:\s*'\/ldt-skill'/);
  assert.match(site, /base = '\/ldt-skill'/);
  assert.match(site, /github\.com\/YoungJibbit95\/ldt-skill/);
  assert.match(release, /REPOSITORY = "YoungJibbit95\/ldt-skill"/);
  assert.match(published, /identity\.repository === 'YoungJibbit95\/ldt-skill'/);
  assert.match(published, /\/ldt-skill\//);
  assert.match(linkChecker, /base = '\/ldt-skill\/'/);
  assert.match(playwright, /\/ldt-skill\/de\//);
});
