import { readdir, readFile, access } from 'node:fs/promises';
import { join, resolve, relative } from 'node:path';
import { parse } from 'parse5';

const root = resolve('dist');
const base = '/ltd-skill/';
async function files(directory) {
  const result = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) result.push(...await files(path));
    else if (entry.name.endsWith('.html')) result.push(path);
  }
  return result;
}
function elements(node) {
  return [node, ...(node.childNodes ?? []).flatMap(elements)];
}
const documents = new Map();
for (const file of await files(root)) {
  const nodes = elements(parse(await readFile(file, 'utf8')));
  documents.set(file, {
    ids: new Set(nodes.flatMap(node => (node.attrs ?? []).filter(a => a.name === 'id').map(a => a.value))),
    links: nodes.flatMap(node => (node.attrs ?? []).filter(a => ['href', 'src'].includes(a.name)).map(a => a.value)),
  });
}
const errors = [];
let checked = 0;
for (const [file, doc] of documents) {
  const pagePath = `${base}${relative(root, file).replaceAll('\\', '/').replace(/index\.html$/, '')}`;
  for (const target of doc.links) {
    if (!target || /^(https?:|mailto:|tel:|data:|javascript:)/.test(target)) continue;
    const url = new URL(target, `https://local.test${pagePath}`);
    if (!url.pathname.startsWith(base)) { errors.push(`${pagePath}: link escapes base: ${target}`); continue; }
    let local = resolve(root, decodeURIComponent(url.pathname.slice(base.length)));
    if (!relative(root, local).startsWith('..')) {
      if (url.pathname.endsWith('/')) local = join(local, 'index.html');
      try { await access(local); } catch { errors.push(`${pagePath}: missing ${target}`); continue; }
      if (url.hash && documents.has(local) && !documents.get(local).ids.has(decodeURIComponent(url.hash.slice(1)))) errors.push(`${pagePath}: missing anchor ${target}`);
      checked++;
    } else errors.push(`${pagePath}: unsafe target ${target}`);
  }
}
const routes = ['', 'docs', 'docs/install', 'docs/guide', 'docs/workflow', 'docs/approvals', 'docs/memory', 'docs/checks', 'docs/registry', 'docs/limits', 'demo', 'built-with-littledevteam'];
for (const page of ['index.html', ...['de', 'en'].flatMap(locale => routes.map(route => `${locale}/${route ? `${route}/` : ''}index.html`))]) {
  if (!documents.has(resolve(root, page))) errors.push(`Required route missing: ${page}`);
}
if (errors.length) { console.error(errors.join('\n')); process.exit(1); }
console.log(`OK: ${checked} internal links/assets/anchors across ${documents.size} built HTML pages; all W1/W2 routes present.`);
