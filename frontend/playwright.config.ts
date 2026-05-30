import { defineConfig, devices } from '@playwright/test';

/**
 * Finch UX/UI test harness.
 *
 * Two kinds of tests live here:
 *  - "ux" tagged tests — drive the running app and capture screenshots for visual
 *    review. These are exploratory; an agent (or human) studies the artifacts.
 *  - regular specs — functional assertions for CI.
 *
 * Auth: `auth.setup.ts` logs in once via Supabase email/password and saves the
 * session to tests/.auth/user.json. Authenticated projects reuse it, so we don't
 * pay the login cost (or burn tokens reasoning about OAuth) on every spec.
 *
 * Run:
 *   npm run e2e                 # all tests, reusing the dev server on :3000
 *   npm run e2e:ux              # just the visual/UX pass
 *   npm run e2e:report          # open the HTML report (screenshots inline)
 */
export default defineConfig({
  testDir: './tests',
  // Screenshots / video / trace land here, grouped per test.
  outputDir: './tests/__artifacts__',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'tests/__report__', open: 'never' }],
  ],
  // Generous timeouts: this app streams (chat/SSE) and hits live market APIs.
  timeout: 60_000,
  expect: { timeout: 10_000 },

  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    // Prefer role/label selectors; this makes getByRole resilient.
    testIdAttribute: 'data-testid',
  },

  projects: [
    // 1. Logs in and persists storage state for everyone else.
    { name: 'setup', testMatch: /auth\.setup\.ts/ },

    // 2. Public surfaces — no auth needed (landing/login page UX).
    {
      name: 'public',
      testMatch: /.*\.public\.spec\.ts/,
      use: { ...devices['Desktop Chrome'] },
    },

    // 3. Authenticated app — reuses the saved session.
    {
      name: 'app',
      testMatch: /.*\.app\.spec\.ts/,
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'tests/.auth/user.json',
      },
    },
  ],

  // Reuse a dev server if one is already up; otherwise start it.
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
