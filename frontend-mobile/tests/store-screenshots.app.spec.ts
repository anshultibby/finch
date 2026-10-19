import { test } from '@playwright/test';
import path from 'path';

/**
 * App Store screenshot capture. These are for the App Store Connect listing,
 * not assertions. Output: tests/__shots__/store/{iphone-6.7,ipad-13}/.
 *
 *   iPhone 6.7": 430 x 932 pt @3x  => 1290 x 2796 px
 *   iPad 13":   1032 x 1376 pt @2x => 2064 x 2752 px
 */

type Page = import('@playwright/test').Page;

const ROOT = path.join(__dirname, '__shots__', 'store');

// Ordered as the listing tells the story: Finch speaks first (home brief),
// then the tools it uses on your behalf.
const SCREENS: { name: string; route: string; ready?: RegExp; prep?: (page: Page) => Promise<void> }[] = [
  // Wait for the brief to finish checking in (the digest is LLM-written and slow).
  { name: '01-home', route: '/', ready: /Your (watchlist|book) today|Finch noticed|All quiet/ },
  { name: '02-screener', route: '/screener', ready: /\d+ matches/ },
  { name: '03-trader', route: '/trader', ready: /Waiting on you/i },
  {
    name: '04-calendar', route: '/calendar', ready: /Earnings/i,
    // The review account's stocks don't report soon; show the whole week.
    prep: async (page) => { await page.getByText('All', { exact: true }).first().click().catch(() => {}); },
  },
  { name: '05-financials', route: '/stock/AAPL?tab=financials', ready: /Revenue/ },
  { name: '06-watching', route: '/watching', ready: /Check-ins/ },
  { name: '07-assistant', route: '/chat', ready: /Recent/ },
];

async function capture(page: Page, dir: string) {
  for (const s of SCREENS) {
    await page.goto(s.route);
    // The review account has no mission set, so the onboarding card can cover the screen.
    const skip = page.getByText('Skip setup for now');
    await skip.waitFor({ state: 'visible', timeout: 4000 }).then(() => skip.click()).catch(() => {});
    if (s.ready) await page.getByText(s.ready).first().waitFor({ timeout: 25_000 }).catch(() => {});
    if (s.prep) await s.prep(page);
    await page.waitForTimeout(1500); // let entering animations finish
    await page.screenshot({ path: path.join(ROOT, dir, `${s.name}.png`), fullPage: false });
  }
}

test.describe('iPhone 6.7"', () => {
  test.use({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 3 });
  test('capture App Store screenshots', async ({ page }) => {
    test.setTimeout(300_000);
    await capture(page, 'iphone-6.7');
  });
});

test.describe('iPad 13"', () => {
  test.use({ viewport: { width: 1032, height: 1376 }, deviceScaleFactor: 2 });
  test('capture App Store screenshots', async ({ page }) => {
    test.setTimeout(300_000);
    await capture(page, 'ipad-13');
  });
});
