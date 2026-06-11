import posthog from 'posthog-js';

// No-ops unless NEXT_PUBLIC_POSTHOG_KEY is set, so local dev and builds
// without a key are unaffected.
const KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY;
const HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://us.i.posthog.com';

let initialized = false;

export function initAnalytics() {
  if (initialized || !KEY || typeof window === 'undefined') return;
  posthog.init(KEY, {
    api_host: HOST,
    capture_pageview: false, // captured manually on App Router route changes
    capture_pageleave: true,
    autocapture: false,
  });
  initialized = true;
}

export function trackPageview() {
  if (!initialized) return;
  posthog.capture('$pageview', { $current_url: window.location.href });
}

export function track(event: string, props?: Record<string, unknown>) {
  if (!initialized) return;
  posthog.capture(event, props);
}

// For events fired right before the window closes (e.g. OAuth popup callbacks).
export function trackBeacon(event: string, props?: Record<string, unknown>) {
  if (!initialized) return;
  posthog.capture(event, props, { transport: 'sendBeacon' });
}

export function identifyUser(userId: string, props?: Record<string, unknown>) {
  if (!initialized) return;
  posthog.identify(userId, props);
}

export function resetAnalytics() {
  if (!initialized) return;
  posthog.reset();
}
