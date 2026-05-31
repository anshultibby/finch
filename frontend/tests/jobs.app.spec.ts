import { test, expect } from '@playwright/test';
import { snap } from './helpers/ux';

// Injects a synthetic /jobs response so the Jobs UI renders fully without the
// DB migration applied.
const NOW = Date.now();
const iso = (ms: number) => new Date(NOW + ms).toISOString();
const JOBS = {
  jobs: [
    { id: 'a1', name: 'NVDA dip alert', message: 'Check if NVDA is below $200. If yes, notify me; otherwise do nothing.', run_at: iso(3 * 3600e3), recurrence: 'weekdays', priority: 2, status: 'pending', created_at: iso(-86400e3), last_run_at: iso(-3600e3), run_count: 4, last_error: null },
    { id: 'b2', name: 'Morning watchlist digest', message: 'Summarize overnight moves and news for my watchlist.', run_at: iso(16 * 3600e3), recurrence: 'daily', priority: 3, status: 'pending', created_at: iso(-2 * 86400e3), last_run_at: iso(-20 * 3600e3), run_count: 12, last_error: null },
    { id: 'c3', name: 'Fed decision reminder', message: 'Remind me 30 min before the FOMC rate decision and summarize expectations.', run_at: iso(5 * 86400e3), recurrence: null, priority: 5, status: 'pending', created_at: iso(-3600e3), last_run_at: null, run_count: 0, last_error: null },
    { id: 'd4', name: 'Earnings recap: AAPL', message: 'After AAPL reports, summarize the print vs estimates and guidance.', run_at: iso(-2 * 86400e3), recurrence: null, priority: 5, status: 'done', created_at: iso(-5 * 86400e3), last_run_at: iso(-2 * 86400e3), run_count: 1, last_error: null },
  ],
  recurring_count: 2, oneoff_count: 1, recurring_limit: 5, oneoff_limit: 10,
};

test.describe('Jobs UI', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test('renders scheduled jobs + history', async ({ page }, testInfo) => {
    await page.route('**/jobs', route => {
      if (route.request().method() === 'GET') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(JOBS) });
      }
      return route.fallback();
    });
    await page.route('**/jobs/register-token', route => route.fulfill({ status: 200, body: '{"ok":true}' }));

    await page.goto('/');
    await expect(page.locator('input[type="password"]')).toHaveCount(0);
    await page.getByRole('button', { name: 'Scheduled' }).first().click();
    await expect(page.getByText(/NVDA dip alert/)).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(400);
    await snap(page, testInfo, '01-jobs');
  });
});
