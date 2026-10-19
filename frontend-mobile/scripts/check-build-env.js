// Runs on EAS (cloud and --local) after install, via the `eas-build-post-install`
// npm hook. A production build without these vars launches into a broken app
// (and once, a crash — the v1.0(20) rejection), so refuse to build it at all.
const REQUIRED = ['EXPO_PUBLIC_SUPABASE_URL', 'EXPO_PUBLIC_SUPABASE_ANON_KEY', 'EXPO_PUBLIC_API_URL'];

if (process.env.EAS_BUILD_PROFILE === 'production') {
  const missing = REQUIRED.filter((k) => !process.env[k]);
  if (missing.length) {
    console.error(`\n✖ Missing production env vars: ${missing.join(', ')}`);
    console.error('  Set them with: eas env:create --environment production\n');
    process.exit(1);
  }
  console.log('✓ Production env vars present');
}
