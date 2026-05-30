import { test, expect } from '@playwright/test';
import { snap, snapResponsive, watchHealth } from './helpers/ux';

/**
 * UX pass over the public landing / sign-in gate.
 * No auth — this is the first impression, so we judge it hard:
 *  - looks right across mobile/tablet/desktop
 *  - the primary CTA and email form are actually usable
 *  - the page is clean (no console errors, no 5xx)
 */
test.describe('Landing page — first impression', () => {
  test('renders cleanly and is responsive', async ({ page }, testInfo) => {
    const health = watchHealth(page);

    await page.goto('/');

    // Hero headline is the anchor of the whole page.
    await expect(
      page.getByRole('heading', { name: /Bloomberg Terminal/i })
    ).toBeVisible();

    // Primary CTA present and inviting.
    await expect(
      page.getByRole('button', { name: /Start with Google/i })
    ).toBeVisible();

    // Email/password fallback is reachable.
    await expect(page.getByPlaceholder('Email')).toBeVisible();
    await expect(page.getByPlaceholder('Password')).toBeVisible();

    // Capture the full first impression at every breakpoint for visual review.
    await snapResponsive(page, testInfo, 'landing');

    // Health: no crashes, no server errors (console/404 noise → warnings).
    health.assertClean();
    await health.warn(testInfo);
  });

  test('sign-up toggle and form interaction feel right', async ({ page }, testInfo) => {
    await page.goto('/');

    // Toggling to sign-up should flip the CTA copy — a small but telling UX detail.
    await page.getByRole('button', { name: /^Sign up$/i }).click();
    await expect(
      page.getByRole('button', { name: /Create account/i })
    ).toBeVisible();
    await snap(page, testInfo, 'signup-mode');

    // Typing into the form should reflect immediately (controlled inputs).
    await page.getByRole('button', { name: /^Sign in$/i }).click();
    await page.getByPlaceholder('Email').fill('demo@example.com');
    await page.getByPlaceholder('Password').fill('hunter2');
    await expect(page.getByPlaceholder('Email')).toHaveValue('demo@example.com');
    await snap(page, testInfo, 'signin-filled');
  });
});
