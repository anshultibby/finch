import { test as setup, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const AUTH_FILE = path.join(__dirname, '.auth/user.json');

// Shared review/test account — credentials are NOT committed.
// Set E2E_EMAIL / E2E_PASSWORD in a gitignored env file (frontend/.env.local).
const EMAIL = process.env.E2E_EMAIL;
const PASSWORD = process.env.E2E_PASSWORD;
if (!EMAIL || !PASSWORD) {
  throw new Error(
    'Set E2E_EMAIL and E2E_PASSWORD (see frontend/.env.local) to run auth setup.'
  );
}

/**
 * Logs in via Supabase email/password and persists the session so the
 * authenticated project (`app`) can skip the gate entirely.
 */
setup('authenticate', async ({ page }) => {
  await page.goto('/');

  // The gate renders the email/password form. Fill and submit.
  await page.getByPlaceholder('Email').fill(EMAIL);
  await page.getByPlaceholder('Password').fill(PASSWORD);
  await page.getByRole('button', { name: /^Sign in$/i }).click();

  // Success = the Supabase auth token lands in localStorage and the gate
  // (password field) disappears. Wait on the durable signal, not a timer.
  await expect
    .poll(
      async () =>
        page.evaluate(() =>
          Object.keys(localStorage).some((k) => /sb-.*auth-token/.test(k))
        ),
      { message: 'Supabase session never appeared — check test credentials', timeout: 20_000 }
    )
    .toBe(true);

  await expect(page.locator('input[type="password"]')).toHaveCount(0);

  fs.mkdirSync(path.dirname(AUTH_FILE), { recursive: true });
  await page.context().storageState({ path: AUTH_FILE });
});
