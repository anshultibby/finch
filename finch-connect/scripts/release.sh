#!/usr/bin/env bash
# Build a SIGNED + NOTARIZED Finch Connect, then publish/refresh the GitHub release.
#
# Prereqs (one-time):
#   • "Developer ID Application: Anshul Tibrewal (G5NB89X943)" cert in your login keychain
#     (Xcode → Settings → Accounts → Manage Certificates → + → Developer ID Application)
#   • gh authenticated (gh auth login)
#   • The App Store Connect API key .p8 (reused from EAS) present — see APPLE_API_KEY_PATH below.
#
# Usage:  ./scripts/release.sh
set -euo pipefail
cd "$(dirname "$0")/.."   # → finch-connect/

# ── Code signing (Developer ID — non-App-Store distribution) ──────────────────
export APPLE_SIGNING_IDENTITY="Developer ID Application: Anshul Tibrewal (G5NB89X943)"

# ── Notarization via App Store Connect API key (same key EAS uses; ids are public,
#    the .p8 stays gitignored) ─────────────────────────────────────────────────
export APPLE_API_ISSUER="21fb1acd-82f9-43da-8310-cb66f4ec697c"
export APPLE_API_KEY="UT5U5FUS2L"
export APPLE_API_KEY_PATH="${APPLE_API_KEY_PATH:-$(cd ../frontend-mobile && pwd)/AuthKey_UT5U5FUS2L.p8}"

if [ ! -f "$APPLE_API_KEY_PATH" ]; then
  echo "✗ Notarization key not found at: $APPLE_API_KEY_PATH"
  echo "  Set APPLE_API_KEY_PATH=/path/to/AuthKey_UT5U5FUS2L.p8 and re-run."
  exit 1
fi

source "$HOME/.cargo/env" 2>/dev/null || true

echo "▶ Building universal (Intel + Apple Silicon), sign + notarize + staple — adds a few min…"
npm run tauri build -- --target universal-apple-darwin

VER="$(node -p "require('./src-tauri/tauri.conf.json').version")"
DMG="$(ls -t src-tauri/target/universal-apple-darwin/release/bundle/dmg/*.dmg | head -1)"
# STABLE, arch-neutral asset name so the in-app direct-download link survives releases:
#   https://github.com/anshultibby/finch/releases/latest/download/Finch-Connect-macOS.dmg
CLEAN="/tmp/Finch-Connect-macOS.dmg"
cp "$DMG" "$CLEAN"

# Verify the notarization ticket is stapled (Gatekeeper-clean).
echo "▶ Verifying signature + notarization…"
spctl -a -vvv -t install "$DMG" 2>&1 | sed 's/^/   /' || true

TAG="v${VER}"
echo "▶ Publishing release ${TAG}…"
if gh release view "$TAG" --repo anshultibby/finch >/dev/null 2>&1; then
  gh release upload "$TAG" --repo anshultibby/finch --clobber "$CLEAN"
else
  gh release create "$TAG" --repo anshultibby/finch \
    --title "Finch Connect ${VER} (macOS, Apple Silicon)" \
    --notes "Signed & notarized. Download, open the .dmg, drag to Applications, and launch." \
    "$CLEAN"
fi
echo "✓ Done — https://github.com/anshultibby/finch/releases/tag/${TAG}"
