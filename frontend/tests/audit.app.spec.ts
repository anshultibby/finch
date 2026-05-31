import { test, expect } from '@playwright/test';
import { snap } from './helpers/ux';

/**
 * UX/UI audit capture. This spec's job is not to assert — it's to produce a
 * broad, reviewable set of screenshots (screens × states × viewports) that a
 * designer/agent studies for polish, hierarchy, spacing, empty states, etc.
 *
 * Each capture is best-effort: one screen failing to load must not block the
 * rest of the sweep.
 */

const DESKTOP = { width: 1440, height: 900 };
const MOBILE = { width: 390, height: 844 };

async function settle(page: any, ms = 1200) {
  await page.waitForTimeout(ms);
}

/** Open a stock detail page via the top-bar search. */
async function openStock(page: any, symbol: string) {
  const search = page.getByPlaceholder(/stocks, crypto/i);
  await search.click();
  await search.fill(symbol);
  await settle(page, 1300);
  const result = page.getByText(new RegExp(symbol === 'AAPL' ? 'Apple' : symbol, 'i')).first();
  if (await result.isVisible().catch(() => false)) await result.click();
  else await search.press('Enter');
  await settle(page, 2000);
}

test.describe('UX audit — desktop sweep', () => {
  test.use({ viewport: DESKTOP });

  test('capture every primary screen', async ({ page }, testInfo) => {
    await page.goto('/');
    await expect(page.locator('input[type="password"]')).toHaveCount(0);
    await settle(page, 1500);

    // 1. Dashboard
    await snap(page, testInfo, '01-dashboard');

    // 2. Top-bar search dropdown (open state)
    const search = page.getByPlaceholder(/stocks, crypto/i);
    await search.click();
    await search.fill('NVDA');
    await settle(page, 1400);
    await snap(page, testInfo, '02-search-dropdown');
    await page.keyboard.press('Escape');

    // 3. Sidebar nav views
    for (const [name, shot] of [
      ['Visualizations', '03-visualizations'],
      ['Memory Store', '04-memory-store'],
    ] as const) {
      const btn = page.getByRole('button', { name }).first();
      if (await btn.isVisible().catch(() => false)) {
        await btn.click();
        await settle(page);
        await snap(page, testInfo, shot);
      }
    }

    // 4. New chat / empty chat composer
    const newChat = page.getByRole('button', { name: /new chat/i }).first();
    if (await newChat.isVisible().catch(() => false)) {
      await newChat.click();
      await settle(page);
      await snap(page, testInfo, '05-chat-empty');
    }

    // 5. Dashboard → Portfolio tab (top tabs on dashboard)
    await page.getByRole('button', { name: 'Dashboard' }).first().click();
    await settle(page);
    for (const tab of ['Earnings', 'Watchlist', 'Portfolio']) {
      const t = page.getByText(new RegExp(`^${tab}$`)).first();
      if (await t.isVisible().catch(() => false)) {
        await t.click();
        await settle(page);
        await snap(page, testInfo, `06-dash-${tab.toLowerCase()}`);
      }
    }
  });

  test('capture stock detail — all tabs', async ({ page }, testInfo) => {
    await page.goto('/');
    await expect(page.locator('input[type="password"]')).toHaveCount(0);
    await openStock(page, 'AAPL');
    await snap(page, testInfo, '10-stock-overview');

    const TABS = ['Earnings', 'Financials', 'News', 'Related', 'Analysis', 'Trades'];
    for (const tab of TABS) {
      const t = page.getByRole('button', { name: new RegExp(`^${tab}$`) }).first();
      const t2 = (await t.isVisible().catch(() => false))
        ? t
        : page.getByText(new RegExp(`^${tab}$`)).first();
      if (await t2.isVisible().catch(() => false)) {
        await t2.click();
        await settle(page, 1600);
        await snap(page, testInfo, `1x-stock-${tab.toLowerCase()}`);
      }
    }
  });
});

test.describe('UX audit — mobile sweep', () => {
  test.use({ viewport: MOBILE });

  test('capture key screens at mobile width', async ({ page }, testInfo) => {
    await page.goto('/');
    await expect(page.locator('input[type="password"]')).toHaveCount(0);
    await settle(page, 1500);
    await snap(page, testInfo, '20-m-dashboard');

    await openStock(page, 'AAPL');
    await snap(page, testInfo, '21-m-stock');

    const newChat = page.getByRole('button', { name: /new chat/i }).first();
    if (await newChat.isVisible().catch(() => false)) {
      await newChat.click();
      await settle(page);
      await snap(page, testInfo, '22-m-chat');
    }
  });
});
