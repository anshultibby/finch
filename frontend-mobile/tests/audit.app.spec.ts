import { test, expect } from '@playwright/test';
import path from 'path';
import { watchHealth } from './helpers/health';

/**
 * UX/UI audit: walk every primary screen at phone width and capture a screenshot
 * for review. Captures are best-effort (a single screen failing to settle must
 * not abort the sweep), but the app must stay healthy — no JS crashes or 5xx.
 *
 * Screenshots land in tests/__shots__/audit/ for a human/agent to study.
 */

const SHOTS = path.join(__dirname, '__shots__', 'audit');

async function settle(page: import('@playwright/test').Page, ms = 1400) {
  // Let SSE streams / live market data populate before capturing.
  await page.waitForTimeout(ms);
}

async function shot(page: import('@playwright/test').Page, name: string) {
  await page.screenshot({ path: path.join(SHOTS, `${name}.png`), fullPage: false });
}

// Tap an in-page tab/label rendered by react-native-web (Text → div).
async function tap(page: import('@playwright/test').Page, label: string) {
  const el = page.getByText(label, { exact: true }).first();
  await el.waitFor({ state: 'visible', timeout: 8000 });
  await el.click();
}

test.describe('mobile UX audit', () => {
  test('capture every primary screen', async ({ page }, testInfo) => {
    const health = watchHealth(page);

    // ── Home: Markets ──────────────────────────────────────────────
    await page.goto('/');
    await settle(page, 2500);
    await shot(page, '01-home-markets');

    // Home tabs (in-page state)
    for (const [i, label] of ['Earnings', 'Watchlist', 'Portfolio'].entries()) {
      try {
        await tap(page, label);
        await settle(page);
        await shot(page, `0${i + 2}-home-${label.toLowerCase()}`);
      } catch (e) {
        testInfo.annotations.push({ type: 'skip', description: `home tab ${label}: ${e}` });
      }
    }
    // back to markets for a clean baseline
    try { await tap(page, 'Markets'); await settle(page); } catch {}

    // ── Stock detail ───────────────────────────────────────────────
    await page.goto('/stock/AAPL');
    await settle(page, 2500);
    await shot(page, '05-stock-overview');
    for (const [i, label] of ['Earnings', 'Financials', 'News', 'Analysis'].entries()) {
      try {
        await tap(page, label);
        await settle(page);
        await shot(page, `0${i + 6}-stock-${label.toLowerCase()}`);
      } catch (e) {
        testInfo.annotations.push({ type: 'skip', description: `stock tab ${label}: ${e}` });
      }
    }

    // ── Chat (empty / welcome) ─────────────────────────────────────
    try {
      await page.goto('/(tabs)/chat/audit-preview');
      await settle(page, 2000);
      await shot(page, '10-chat-empty');
    } catch (e) {
      testInfo.annotations.push({ type: 'skip', description: `chat: ${e}` });
    }

    // ── Profile / Settings / Privacy / Notifications ───────────────
    const routes: [string, string][] = [
      ['/(tabs)/profile', '11-profile'],
      ['/settings', '12-settings'],
      ['/notification-settings', '13-notification-settings'],
      ['/privacy', '14-privacy'],
      ['/notifications', '15-notifications'],
    ];
    for (const [route, name] of routes) {
      try {
        await page.goto(route);
        await settle(page, 1600);
        await shot(page, name);
      } catch (e) {
        testInfo.annotations.push({ type: 'skip', description: `${route}: ${e}` });
      }
    }

    await health.report(testInfo);
    health.assertNoCrashes();
  });

  test('search surfaces results', async ({ page }) => {
    await page.goto('/');
    await settle(page, 2000);
    await page.getByTestId('search-button').click({ timeout: 8000 });
    await page.getByTestId('search-input').fill('NVDA', { timeout: 8000 });
    await settle(page, 1800);
    await shot(page, '20-search-nvda');
    // Results render as tappable rows; the symbol should be visible.
    await expect(page.getByText('NVDA').first()).toBeVisible();
  });
});
