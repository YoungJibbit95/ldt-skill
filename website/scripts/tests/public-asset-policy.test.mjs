import { test } from 'node:test';
import assert from 'node:assert/strict';
import { assetPolicy } from '../public-asset-policy.mjs';
const base = 'https://youngjibbit95.github.io/ldt-skill/';
test('all HTTP asset classes and Pagefind data must use the approved origin and base', () => {
  for (const type of ['script', 'stylesheet', 'font', 'image', 'fetch', 'xhr']) {
    assert.deepEqual(assetPolicy(`${base}assets/a.bin`, type, base), { checked: true, allowed: true });
    assert.deepEqual(assetPolicy('https://external.example/assets/a.bin', type, base), { checked: true, allowed: false });
    assert.deepEqual(assetPolicy('https://youngjibbit95.github.io/elsewhere/a.bin', type, base), { checked: true, allowed: false });
  }
  assert.deepEqual(assetPolicy('https://external.example/pagefind/index.pf_meta', 'other', base), { checked: true, allowed: false });
  assert.deepEqual(assetPolicy(`${base}../pagefind/index.pf_meta`, 'fetch', base), { checked: true, allowed: false });
});
test('intentional navigation links and in-document assets are exempt', () => {
  assert.deepEqual(assetPolicy('https://github.com/YoungJibbit95/ldt-skill', 'document', base), { checked: false, allowed: true });
  assert.deepEqual(assetPolicy('data:image/svg+xml,test', 'image', base), { checked: false, allowed: true });
});
