import { defineConfig } from '@playwright/test'

const phone = { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 }
const desktop = { viewport: { width: 1280, height: 800 } }

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.ts',
  timeout: 180_000,
  expect: { timeout: 20_000 },
  fullyParallel: true,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:3000',
    trace: 'retain-on-failure',
    navigationTimeout: 60_000,
  },
  projects: [
    { name: 'desktop', use: { ...desktop, colorScheme: 'light' } },
    { name: 'phone', use: { ...phone, colorScheme: 'light' } },
    { name: 'desktop-dark', use: { ...desktop, colorScheme: 'dark' } },
    { name: 'phone-dark', use: { ...phone, colorScheme: 'dark' } },
  ],
})
