import { test, expect } from '@playwright/test';
import { snap } from './helpers/ux';

// Injects a synthetic connected portfolio so the Analytics view renders fully.
// The analytics computation + AI narration still run for real on the backend.
const DEMO_PORTFOLIO = {
  success: true,
  accounts: [{
    id: 'demo', name: 'Demo Brokerage', number: 'X', type: 'margin', institution: 'Demo',
    balance: 0, total_value: 87000, position_count: 7,
    positions: [
      { symbol: 'AAPL', quantity: 80, price: 312, value: 25000 },
      { symbol: 'MSFT', quantity: 40, price: 500, value: 20000 },
      { symbol: 'NVDA', quantity: 85, price: 211, value: 18000 },
      { symbol: 'JNJ', quantity: 35, price: 228, value: 8000 },
      { symbol: 'JPM', quantity: 25, price: 280, value: 7000 },
      { symbol: 'XOM', quantity: 45, price: 110, value: 5000 },
      { symbol: 'KO', quantity: 60, price: 66, value: 4000 },
    ],
  }],
  total_value: 87000, total_positions: 7, account_count: 1, message: 'ok',
};

test.describe('Portfolio Analytics', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test('renders allocation, risk, dividends + AI narration', async ({ page }, testInfo) => {
    await page.route('**/snaptrade/portfolio/**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(DEMO_PORTFOLIO) }));

    await page.goto('/');
    await expect(page.locator('input[type="password"]')).toHaveCount(0);

    await page.getByRole('button', { name: 'Analytics' }).first().click();
    // Wait for the analyzed view (beta metric + narration require backend + LLM).
    await expect(page.getByText(/Portfolio beta/i)).toBeVisible({ timeout: 40000 });
    await expect(page.getByText(/Sector allocation/i)).toBeVisible();
    await page.waitForTimeout(800);
    await snap(page, testInfo, '01-analytics');
  });
});
