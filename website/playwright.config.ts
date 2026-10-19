import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  workers: process.env.CI ? 2 : 3,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: { baseURL: 'http://127.0.0.1:4321', trace: 'retain-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: `"${process.execPath}" node_modules/astro/bin/astro.mjs preview --host 127.0.0.1 --port 4321`,
    url: 'http://127.0.0.1:4321/ldt-skill/de/',
    reuseExistingServer: !process.env.CI,
    timeout: 60000,
  },
});
