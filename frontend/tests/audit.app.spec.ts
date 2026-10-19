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

// The review account has no mission set, so the onboarding card may cover the app.
async function skipMissionCard(page: import('@playwright/test').Page) {
  const skip = page.getByText('Skip setup for now');
  if (await skip.isVisible().catch(() => false)) {
    await skip.click();
    await page.waitForTimeout(600);
  }
}

test.describe('UX audit — desktop sweep', () => {
  test.use({ viewport: DESKTOP });

  test('capture every primary screen', async ({ page }, testInfo) => {
    await page.goto('/');
    await expect(page.locator('input[type="password"]')).toHaveCount(0);
    await settle(page, 1500);

    await skipMissionCard(page);

    // 1. Proactive home (brief + six cards)
    await snap(page, testInfo, '01-home');

    // 2. Top-bar search dropdown (open state)
    const search = page.getByPlaceholder(/stocks, crypto/i);
    await search.click();
    await search.fill('NVDA');
    await settle(page, 1400);
    await snap(page, testInfo, '02-search-dropdown');
    await page.keyboard.press('Escape');

    // 3. Each home card's destination, then back home via the sidebar.
    for (const [card, shot] of [
      ['assistant', '03-assistant'],
      ['screener', '04-screener'],
      ['trader', '05-trader'],
      ['financials', '06-financials'],
      ['calendar', '07-calendar'],
      ['watching', '08-watching'],
    ] as const) {
      await page.getByTestId(`home-card-${card}`).click();
      await settle(page, 2000);
      await snap(page, testInfo, shot);
      await page.getByRole('button', { name: 'Home' }).first().click();
      await settle(page, 600);
    }

    // 4. New chat / empty chat composer
    const newChat = page.getByRole('button', { name: /new chat/i }).first();
    if (await newChat.isVisible().catch(() => false)) {
      await newChat.click();
      await settle(page);
      await snap(page, testInfo, '09-chat-empty');
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
    await skipMissionCard(page);
    await snap(page, testInfo, '20-m-home');

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
