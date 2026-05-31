import { defineConfig, devices } from '@playwright/test';

/**
 * Finch mobile (Expo) UX/UI test harness.
 *
 * The app ships to iOS/Android, but Expo also builds for the web via
 * react-native-web. We drive that web build with Playwright so we can capture
 * screenshots of every screen at phone width and assert the app stays healthy
 * (no JS crashes / 5xx) — without a simulator in the loop.
 *
 * Auth: `auth.setup.ts` logs in once via Supabase email/password and saves the
 * session to tests/.auth/user.json. The authenticated `app` project reuses it.
 *
 * Run (backend must be up on :8000):
 *   npm run e2e          # auth + full audit screenshot pass
 *   npm run e2e:report   # open the HTML report (screenshots inline)
 */

const PHONE = { width: 390, height: 844 }; // iPhone 14-ish

export default defineConfig({
  testDir: './tests',
  outputDir: './tests/__artifacts__',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'tests/__report__', open: 'never' }],
  ],
  // Generous: Expo's first web bundle is slow, and the app streams (SSE) and
  // hits live market APIs.
  timeout: 90_000,
  expect: { timeout: 15_000 },

  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:8081',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    viewport: PHONE,
  },

  projects: [
    { name: 'setup', testMatch: /auth\.setup\.ts/ },
    {
      name: 'app',
      testMatch: /.*\.app\.spec\.ts/,
      dependencies: ['setup'],
      use: {
        ...devices['Desktop Chrome'],
        viewport: PHONE,
        storageState: 'tests/.auth/user.json',
      },
    },
  ],

  webServer: {
    command: 'npx expo start --web --port 8081',
    env: {
      EXPO_PUBLIC_API_URL: 'http://localhost:8000',
      CI: '1', // non-interactive; don't auto-open a browser
      BROWSER: 'none',
    },
    url: 'http://localhost:8081',
    reuseExistingServer: true,
    timeout: 180_000,
  },
});
