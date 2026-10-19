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
  await el.click({ timeout: 8000 });
}

test.describe('mobile UX audit', () => {
  test('capture every primary screen', async ({ page }, testInfo) => {
    test.setTimeout(240_000);
    const health = watchHealth(page);

    // ── Home + the six card destinations ───────────────────────────
    await page.goto('/');
    await settle(page, 2500);
    await shot(page, '01-home');

    const cards: [string, string][] = [
      ['/chat', '02-assistant'],
      ['/screener', '03-screener'],
      ['/trader', '04-trader'],
      ['/research', '05-financials'],
      ['/calendar', '06-calendar'],
      ['/watching', '07-watching'],
      ['/portfolio', '08-portfolio'],
      ['/markets', '09-markets'],
      ['/watchlist', '09b-watchlist'],
    ];
    for (const [route, name] of cards) {
      try {
        await page.goto(route);
        await settle(page, 2000);
        await shot(page, name);
      } catch (e) {
        testInfo.annotations.push({ type: 'skip', description: `${route}: ${e}` });
      }
    }

    // ── Stock detail ───────────────────────────────────────────────
    await page.goto('/stock/AAPL');
    await settle(page, 2500);
    await shot(page, '10-stock-overview');
    for (const [i, label] of ['Earnings', 'Financials', 'News', 'Analysis'].entries()) {
      try {
        await tap(page, label);
        await settle(page);
        await shot(page, `${i + 11}-stock-${label.toLowerCase()}`);
      } catch (e) {
        testInfo.annotations.push({ type: 'skip', description: `stock tab ${label}: ${e}` });
      }
    }

    // ── Chat (empty / welcome) ─────────────────────────────────────
    try {
      await page.goto('/(tabs)/chat/audit-preview');
      await settle(page, 2000);
      await shot(page, '15-chat-empty');
    } catch (e) {
      testInfo.annotations.push({ type: 'skip', description: `chat: ${e}` });
    }

    // ── Profile / Settings / Privacy / Notifications ───────────────
    const routes: [string, string][] = [
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
    // Header search opens the Financials screen's search.
    await page.goto('/');
    await settle(page, 2000);
    await page.getByLabel('Search stocks').click({ timeout: 8000 });
    await page.getByTestId('research-search').fill('NVDA', { timeout: 8000 });
    await settle(page, 1800);
    await shot(page, '20-search-nvda');
    // Results render as tappable rows; the symbol should be visible.
    await expect(page.getByText('NVDA').first()).toBeVisible();
  });
});
