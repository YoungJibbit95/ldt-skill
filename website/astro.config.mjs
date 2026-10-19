import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  site: 'https://youngjibbit95.github.io',
  base: '/ldt-skill',
  trailingSlash: 'always',
  integrations: [starlight({
    title: 'LittleDevTeam',
    description: 'Architecture first. Build together.',
    defaultLocale: 'de',
    locales: { de: { label: 'Deutsch', lang: 'de' }, en: { label: 'English', lang: 'en' } },
    favicon: '/favicon.svg',
    disable404Route: true,
    expressiveCode: { defaultProps: { wrap: true } },
    customCss: ['./src/styles/global.css', './src/styles/docs.css'],
    components: {
      Header: './src/components/DocsHeader.astro',
      ThemeProvider: './src/components/DarkTheme.astro',
      ThemeSelect: './src/components/Empty.astro',
    },
    sidebar: [{
      label: 'Hier beginnt dein Projekt',
      translations: { en: 'Start your project here' },
      items: [
        { slug: 'docs', label: 'Überblick', translations: { en: 'Overview' } },
        { slug: 'docs/install', label: 'Installation', translations: { en: 'Installation' } },
        { slug: 'docs/guide', label: 'Dein erster Auftrag', translations: { en: 'Your first task' } },
      ],
    }, {
      label: 'Workflow & Referenz',
      translations: { en: 'Workflow & reference' },
      items: [
        { slug: 'docs/workflow', label: 'Ablauf & Profile', translations: { en: 'Lifecycle & profiles' } },
        { slug: 'docs/approvals', label: 'Freigaben & Review', translations: { en: 'Approvals & review' } },
        { slug: 'docs/memory', label: 'Zustände & Snapshots', translations: { en: 'State & snapshots' } },
        { slug: 'docs/checks', label: 'Prüfbefehle', translations: { en: 'Validator commands' } },
        { slug: 'docs/registry', label: 'Registry & externe Skills', translations: { en: 'Registry & external skills' } },
        { slug: 'docs/limits', label: 'Grenzen & Wiederaufnahme', translations: { en: 'Limits & recovery' } },
      ],
    }],
    editLink: { baseUrl: 'https://github.com/YoungJibbit95/ldt-skill/edit/main/website/' },
    lastUpdated: false,
    pagination: true,
  })],
});
