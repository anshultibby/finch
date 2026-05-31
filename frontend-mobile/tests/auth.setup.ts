import { test as setup, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const AUTH_FILE = path.join(__dirname, '.auth/user.json');

// Shared App Store review / test account. Override via env.
const EMAIL = process.env.E2E_EMAIL || 'appstore.review@finchapp.ai';
const PASSWORD = process.env.E2E_PASSWORD || 'FinchApp';

/**
 * Logs in via Supabase email/password and persists the session so the
 * authenticated `app` project can skip the login screen entirely.
 *
 * On web, supabase-js stores its token in localStorage (key `sb-*-auth-token`),
 * exactly like the web frontend — so storageState carries the session forward.
 */
setup('authenticate', async ({ page }) => {
  await page.goto('/');

  // Reveal the email form (the default CTA is "Continue with Google").
  await page.getByText('Sign in with email').click();

  await page.getByPlaceholder('Email').fill(EMAIL);
  await page.getByPlaceholder('Password').fill(PASSWORD);
  await page.getByText('Sign in', { exact: true }).click();

  // Success = the Supabase auth token lands in localStorage. Wait on that
  // durable signal rather than a timer.
  await expect
    .poll(
      async () =>
        page.evaluate(() =>
          Object.keys(localStorage).some((k) => /sb-.*auth-token/.test(k))
        ),
      { message: 'Supabase session never appeared — check test credentials', timeout: 30_000 }
    )
    .toBe(true);

  fs.mkdirSync(path.dirname(AUTH_FILE), { recursive: true });
  await page.context().storageState({ path: AUTH_FILE });
});
