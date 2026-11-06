import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  workers: 1,
  use: { baseURL: process.env.NOURISHON_E2E_URL ?? 'http://127.0.0.1:5173', browserName: 'chromium', headless: true },
})
