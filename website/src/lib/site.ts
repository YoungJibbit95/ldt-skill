export type Locale = 'de' | 'en';
export const base = '/ldt-skill';
export const repository = 'https://github.com/YoungJibbit95/ldt-skill';
export const sourceRevision = '9a062eb9de0990ce1074dd677d26e5a528ee14a0';
export const pathFor = (locale: Locale, page = '') => `${base}/${locale}/${page ? `${page.replace(/^\/+|\/+$/g, '')}/` : ''}`;
export const otherLocale = (locale: Locale): Locale => locale === 'de' ? 'en' : 'de';
export function translatedPath(pathname: string, locale: Locale) {
  return pathname.replace(/\/(de|en)(\/|$)/, `/${otherLocale(locale)}$2`);
}
