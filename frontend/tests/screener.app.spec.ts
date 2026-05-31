import { test, expect } from '@playwright/test';
import { snap } from './helpers/ux';

test.describe('Screener', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test('AI prompt + manual filters return results', async ({ page }, testInfo) => {
    await page.goto('/');
    await expect(page.locator('input[type="password"]')).toHaveCount(0);

    // Navigate via sidebar
    await page.getByRole('button', { name: 'Screener' }).first().click();
    await page.waitForTimeout(800);
    await snap(page, testInfo, '01-screener-empty');

    // AI path
    const ai = page.getByPlaceholder(/profitable large-cap|low volatility/i);
    await ai.fill('low-beta healthcare dividend payers over $10B market cap');
    await page.getByRole('button', { name: /^Screen$/ }).click();
    // Wait for results (LLM + FMP can take a few seconds)
    await expect(page.getByText(/matches/i)).toBeVisible({ timeout: 30000 });
    await page.waitForTimeout(500);
    await snap(page, testInfo, '02-screener-ai-results');

    // Manual path: change sector + run
    await page.getByRole('button', { name: /Run screen/i }).click();
    await expect(page.getByText(/matches/i)).toBeVisible({ timeout: 20000 });
    await snap(page, testInfo, '03-screener-manual');
  });
});
