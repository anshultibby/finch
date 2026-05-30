import { Page, TestInfo, expect } from '@playwright/test';
export type { TestInfo };
import fs from 'fs';
import path from 'path';

/**
 * UX testing helpers — built so an agent (or human) can *study* the output, not
 * just get a pass/fail. Every screenshot is written to a flat, predictable folder
 * (tests/__shots__/<spec>/<name>.png) so they're easy to open and review in bulk.
 */

const SHOTS_ROOT = path.join(__dirname, '..', '__shots__');

function specSlug(testInfo: TestInfo): string {
  return path
    .basename(testInfo.file)
    .replace(/\.(app|public)\.spec\.ts$/, '')
    .replace(/\.spec\.ts$/, '');
}

/** Take a labelled, full-page screenshot into the reviewable shots folder. */
export async function snap(
  page: Page,
  testInfo: TestInfo,
  name: string,
  opts: { fullPage?: boolean } = {}
): Promise<string> {
  const dir = path.join(SHOTS_ROOT, specSlug(testInfo));
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `${name.replace(/[^\w-]+/g, '_')}.png`);
  await page.screenshot({ path: file, fullPage: opts.fullPage ?? true });
  // Also attach to the HTML report so it shows up inline.
  await testInfo.attach(name, { path: file, contentType: 'image/png' });
  return file;
}

/** Capture the same view across the breakpoints that matter for this app. */
export const VIEWPORTS = [
  { name: 'mobile', width: 390, height: 844 }, // iPhone 14-ish
  { name: 'tablet', width: 820, height: 1180 }, // iPad
  { name: 'desktop', width: 1440, height: 900 },
] as const;

export async function snapResponsive(
  page: Page,
  testInfo: TestInfo,
  baseName: string
): Promise<void> {
  for (const vp of VIEWPORTS) {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    // Let layout settle (debounced resize listeners, charts re-measuring).
    await page.waitForTimeout(400);
    await snap(page, testInfo, `${baseName}-${vp.name}`);
  }
}

/**
 * Collect console errors + failed network requests while a flow runs, so the UX
 * test can assert the page is *clean*, not just visually present. Returns a
 * getter you read at the end of the test.
 */
export function watchHealth(page: Page) {
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const serverErrors: string[] = []; // 5xx — always a real problem
  const notFound: string[] = []; // 4xx (incl 404) — surfaced as a warning

  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', (err) => pageErrors.push(String(err)));
  page.on('response', (res) => {
    const status = res.status();
    if (status >= 500) serverErrors.push(`${status} ${res.url()}`);
    else if (status >= 400 && status !== 401) notFound.push(`${status} ${res.url()}`);
  });

  return {
    get consoleErrors() {
      return consoleErrors;
    },
    get pageErrors() {
      return pageErrors;
    },
    get serverErrors() {
      return serverErrors;
    },
    get notFound() {
      return notFound;
    },
    /**
     * Hard assertion — only for things that are unambiguously broken:
     * uncaught JS exceptions (the page crashed) and 5xx responses.
     * Console errors and 4xx/404s are reported via warn() instead, because
     * benign third-party/favicon/probe noise shouldn't make a UX run flaky.
     */
    assertClean() {
      expect(pageErrors, `Uncaught page errors:\n${pageErrors.join('\n')}`).toEqual([]);
      expect(serverErrors, `Server (5xx) failures:\n${serverErrors.join('\n')}`).toEqual([]);
    },
    /** Attach non-fatal findings to the report for human/agent review. */
    async warn(testInfo: TestInfo) {
      const noisy = meaningfulConsoleErrors(consoleErrors);
      const lines: string[] = [];
      if (noisy.length) lines.push(`Console errors:\n  - ${noisy.join('\n  - ')}`);
      if (notFound.length) lines.push(`4xx responses:\n  - ${notFound.join('\n  - ')}`);
      if (lines.length) {
        const body = lines.join('\n\n');
        testInfo.annotations.push({ type: 'warning', description: body });
        await testInfo.attach('ux-warnings.txt', {
          body,
          contentType: 'text/plain',
        });
        // eslint-disable-next-line no-console
        console.warn(`\n⚠️  UX warnings in "${testInfo.title}":\n${body}\n`);
      }
    },
  };
}

/** Filter known-noisy console messages so a UX warning report is signal-rich. */
export function meaningfulConsoleErrors(errors: string[]): string[] {
  const IGNORE = [
    /ResizeObserver loop/i,
    /Download the React DevTools/i,
    /\[Fast Refresh\]/i,
    /hydration/i, // dev-only hydration noise; track separately if you care
  ];
  return errors.filter((e) => !IGNORE.some((re) => re.test(e)));
}
