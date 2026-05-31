import { test } from '@playwright/test';
import path from 'path';

/**
 * App Store screenshot capture at the required 6.7" iPhone resolution
 * (1290 x 2796 = 430pt viewport @ 3x). Output: tests/__shots__/store/.
 * These are for the App Store Connect listing, not assertions.
 */

// 430 x 932 logical @ deviceScaleFactor 3 => 1290 x 2796 physical pixels.
test.use({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 3 });

const STORE = path.join(__dirname, '__shots__', 'store');

async function settle(page: import('@playwright/test').Page, ms = 2200) {
  await page.waitForTimeout(ms);
}
async function shot(page: import('@playwright/test').Page, name: string) {
  await page.screenshot({ path: path.join(STORE, `${name}.png`), fullPage: false });
}
async function tap(page: import('@playwright/test').Page, label: string) {
  const el = page.getByText(label, { exact: true }).first();
  await el.waitFor({ state: 'visible', timeout: 8000 });
  await el.click();
}

test('capture App Store screenshots (6.7")', async ({ page }) => {
  // 1. Markets home
  await page.goto('/');
  await settle(page, 3000);
  await shot(page, '01-markets');

  // 2. Watchlist
  try { await tap(page, 'Watchlist'); await settle(page); await shot(page, '02-watchlist'); } catch {}
  // 3. Earnings
  try { await tap(page, 'Earnings'); await settle(page); await shot(page, '03-earnings'); } catch {}

  // 4. Stock detail
  await page.goto('/stock/AAPL');
  await settle(page, 3000);
  await shot(page, '04-stock');

  // 5. Chat welcome
  await page.goto('/(tabs)/chat/store-preview');
  await settle(page, 2200);
  await shot(page, '05-chat');
});
