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
test('capture App Store screenshots (6.7")', async ({ page }) => {
  // Ordered as the listing tells the story: Finch speaks first (home brief),
  // then the tools it uses on your behalf.
  const screens: [string, string, number][] = [
    ['01-home', '/', 4000],
    ['02-screener', '/screener', 3500],
    ['03-trader', '/trader', 3500],
    ['04-calendar', '/calendar', 3500],
    ['05-financials', '/stock/AAPL?tab=financials', 4000],
    ['06-watching', '/watching', 3500],
    ['07-assistant', '/chat', 3500],
  ];
  for (const [name, route, wait] of screens) {
    await page.goto(route);
    await settle(page, wait);
    // The review account has no mission set, so the onboarding card can cover the screen.
    const skip = page.getByText('Skip setup for now');
    if (await skip.isVisible().catch(() => false)) { await skip.click(); await settle(page, 800); }
    await shot(page, name);
  }
});
