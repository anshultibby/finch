import { test, expect } from '@playwright/test';
import { snap, watchHealth } from './helpers/ux';

/**
 * Authenticated UX tour. Reuses the saved session (see playwright.config `app`
 * project). Walks the primary views the way a new user would, screenshotting
 * each so the layouts can be studied for spacing, overflow, empty states, and
 * loading polish — not just "did it render".
 */

// Sidebar nav targets. Accessible name comes from the visible label (expanded
// sidebar) or the title tooltip (collapsed) — getByRole handles both.
const NAV = [
  { name: 'Dashboard', shot: 'dashboard' },
  { name: 'Visualizations', shot: 'visualizations' },
  { name: 'Memory Store', shot: 'memory-store' },
] as const;

test.describe('Authenticated app tour', () => {
  test('lands on the dashboard without errors', async ({ page }, testInfo) => {
    const health = watchHealth(page);
    await page.goto('/');

    // App shell present = we're past the gate.
    await expect(page.locator('input[type="password"]')).toHaveCount(0);
    // Give live market widgets a moment to populate before judging the view.
    await page.waitForLoadState('networkidle').catch(() => {});
    await page.waitForTimeout(1500);

    await snap(page, testInfo, 'dashboard-initial');

    health.assertClean(); // hard-fail only on crashes / 5xx
    await health.warn(testInfo); // surface console errors + 404s as warnings
  });

  test('each primary view renders a reviewable screen', async ({ page }, testInfo) => {
    const health = watchHealth(page);
    await page.goto('/');
    await expect(page.locator('input[type="password"]')).toHaveCount(0);

    for (const item of NAV) {
      const btn = page.getByRole('button', { name: item.name }).first();
      await expect(btn, `Nav button "${item.name}" should exist`).toBeVisible();
      await btn.click();
      // Settle: SPA view swap + any data fetch.
      await page.waitForTimeout(1200);
      await snap(page, testInfo, item.shot);
    }

    health.assertClean();
    await health.warn(testInfo);
  });

  test('global stock search opens a stock detail view', async ({ page }, testInfo) => {
    await page.goto('/');
    await expect(page.locator('input[type="password"]')).toHaveCount(0);

    // Top bar search — type a ticker, pick the result, land on the stock page.
    // NB: target the stock search specifically; the sidebar also has a
    // "Search chats..." box that a loose /search/i would match first.
    const search = page.getByPlaceholder(/stocks, crypto/i);
    await expect(search).toBeVisible();
    await search.fill('AAPL');
    await page.waitForTimeout(1200); // debounced (250ms) + network

    // Click the first result if the dropdown rendered one; otherwise Enter.
    const firstResult = page.getByText(/Apple/i).first();
    if (await firstResult.isVisible().catch(() => false)) {
      await firstResult.click();
    } else {
      await search.press('Enter');
    }
    await page.waitForTimeout(2000);
    await snap(page, testInfo, 'stock-AAPL');

    // We should now see something AAPL-specific on screen.
    await expect(page.getByText(/AAPL/).first()).toBeVisible();
  });
});
