const assetTypes = new Set(['font', 'stylesheet', 'script', 'image', 'fetch', 'xhr', 'media', 'manifest']);

export function assetPolicy(url, resourceType, base) {
  const parsed = new URL(url);
  const http = ['http:', 'https:'].includes(parsed.protocol);
  const checked = http && resourceType !== 'document' && (assetTypes.has(resourceType) || /pagefind/i.test(parsed.pathname));
  const approved = new URL(base);
  return { checked, allowed: !checked || (parsed.origin === approved.origin && parsed.pathname.startsWith(approved.pathname)) };
}
