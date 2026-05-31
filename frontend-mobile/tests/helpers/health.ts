import type { Page, TestInfo } from '@playwright/test';

/**
 * Lightweight health watcher: collects console errors, uncaught page errors, and
 * HTTP failures while a spec drives the app. We hard-fail only on real breakage
 * (JS crashes + 5xx); 4xx and noisy console warnings are recorded but tolerated,
 * since live market endpoints and third-party scripts produce benign noise.
 */
export function watchHealth(page: Page) {
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const serverErrors: string[] = [];

  const IGNORE = [
    'ResizeObserver',
    'Download the React DevTools',
    'React DevTools',
    '[Fast Refresh]',
    'Warning: ',           // RN-web/React dev warnings
    'shadow',              // RN-web deprecation noise
    'props.pointerEvents', // RN-web deprecation noise
    'style.resize',
    'useNativeDriver',
    'favicon',
  ];

  page.on('console', (msg) => {
    if (msg.type() !== 'error') return;
    const text = msg.text();
    if (IGNORE.some((s) => text.includes(s))) return;
    consoleErrors.push(text);
  });

  page.on('pageerror', (err) => {
    pageErrors.push(err.message);
  });

  page.on('response', (res) => {
    if (res.status() >= 500) {
      serverErrors.push(`${res.status()} ${res.request().method()} ${res.url()}`);
    }
  });

  return {
    async report(testInfo: TestInfo) {
      const lines: string[] = [];
      if (consoleErrors.length) lines.push(`Console errors:\n  ${consoleErrors.slice(0, 20).join('\n  ')}`);
      if (serverErrors.length) lines.push(`5xx responses:\n  ${serverErrors.slice(0, 20).join('\n  ')}`);
      if (pageErrors.length) lines.push(`Uncaught page errors:\n  ${pageErrors.slice(0, 20).join('\n  ')}`);
      if (lines.length) {
        await testInfo.attach('health.txt', { body: lines.join('\n\n'), contentType: 'text/plain' });
      }
      return { consoleErrors, pageErrors, serverErrors };
    },
    // Hard failures only: a crash or a server error means the app is broken.
    assertNoCrashes() {
      const fatal = [...pageErrors, ...serverErrors];
      if (fatal.length) {
        throw new Error(`App health check failed:\n${fatal.join('\n')}`);
      }
    },
  };
}
