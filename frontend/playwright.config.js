import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.E2E_BASE_URL || 'http://localhost:5173';
const apiURL = process.env.E2E_API_URL || 'http://localhost:8000';
const isolatedMode = process.env.E2E_ISOLATED === '1';
const workerCount = Number(process.env.E2E_WORKERS || 1);

function assertSafeLocalUrl(value, label) {
  const url = new URL(value);
  const loopbackHosts = new Set(['localhost', '127.0.0.1', '[::1]']);
  if (!loopbackHosts.has(url.hostname)) {
    throw new Error(
      `${label} debe apuntar a localhost para las pruebas E2E aisladas.`,
    );
  }
}

assertSafeLocalUrl(baseURL, 'E2E_BASE_URL');
assertSafeLocalUrl(apiURL, 'E2E_API_URL');

if (!Number.isInteger(workerCount) || workerCount < 1) {
  throw new Error('E2E_WORKERS debe ser un entero positivo.');
}

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  workers: workerCount,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  webServer: process.env.E2E_BASE_URL ? undefined : {
    command: 'npm run dev -- --host 127.0.0.1 --port 5173 --strictPort',
    url: baseURL,
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      ...process.env,
      VITE_API_URL: apiURL,
    },
  },
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'setup',
      testMatch: /auth\.setup\.js/,
    },
    {
      name: 'chromium',
      dependencies: ['setup'],
      testIgnore: /auth\.setup\.js/,
      use: {
        ...devices['Desktop Chrome'],
        storageState: isolatedMode
          ? { cookies: [], origins: [] }
          : '.playwright/.auth/tenant.json',
      },
    },
  ],
});
