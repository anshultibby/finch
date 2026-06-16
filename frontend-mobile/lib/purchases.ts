/**
 * RevenueCat (Apple In-App Purchase) wrapper — the iOS Pro subscription.
 *
 * App Store guideline 3.1.1 requires paid digital content to be purchasable via
 * In-App Purchase. This module is the only place the app talks to StoreKit; the
 * backend stays the source of truth for `plan`/`credits` and is updated by the
 * RevenueCat webhook (POST /credits/revenuecat-webhook).
 *
 * It is a no-op on web and Android, or whenever EXPO_PUBLIC_REVENUECAT_IOS_KEY
 * is unset (e.g. Expo Go / local dev without a dev build), so callers never need
 * to branch on platform — they just get `null`/`false` back.
 */
import { Platform } from 'react-native';
import type {
  default as PurchasesType,
  PurchasesPackage,
  CustomerInfo,
} from 'react-native-purchases';

/** Entitlement identifier configured in the RevenueCat dashboard. */
export const PRO_ENTITLEMENT = 'pro';

const IOS_API_KEY = process.env.EXPO_PUBLIC_REVENUECAT_IOS_KEY || '';

let _purchases: typeof PurchasesType | null = null;
let _configured = false;

/** Lazily resolve the native module; returns null where IAP can't run. */
function rc(): typeof PurchasesType | null {
  if (Platform.OS !== 'ios' || !IOS_API_KEY) return null;
  if (!_purchases) {
    try {
      // Required (not imported) so web/Android bundles never pull in the native module.
      _purchases = require('react-native-purchases').default;
    } catch {
      return null;
    }
  }
  return _purchases;
}

/** True when IAP is actually available on this build. */
export function purchasesAvailable(): boolean {
  return rc() !== null;
}

/** Configure the SDK once. Safe to call repeatedly. */
export function initPurchases(): void {
  const P = rc();
  if (!P || _configured) return;
  try {
    P.configure({ apiKey: IOS_API_KEY });
    _configured = true;
  } catch (e) {
    console.error('RevenueCat configure failed:', e);
  }
}

/**
 * Associate purchases with the signed-in Supabase user. The backend webhook
 * keys off this id (event.app_user_id), so it must run before any purchase.
 */
export async function identifyUser(userId: string): Promise<void> {
  const P = rc();
  if (!P) return;
  initPurchases();
  try {
    await P.logIn(userId);
  } catch (e) {
    console.error('RevenueCat logIn failed:', e);
  }
}

/** Detach the current user (call on sign-out). */
export async function logoutPurchases(): Promise<void> {
  const P = rc();
  if (!P || !_configured) return;
  try {
    await P.logOut();
  } catch {
    // logOut throws if already anonymous — harmless.
  }
}

function hasProEntitlement(info: CustomerInfo): boolean {
  return info.entitlements.active[PRO_ENTITLEMENT] !== undefined;
}

/** The monthly Pro package to sell, or null if offerings aren't available. */
export async function getProPackage(): Promise<PurchasesPackage | null> {
  const P = rc();
  if (!P) return null;
  try {
    const offerings = await P.getOfferings();
    const current = offerings.current;
    if (!current) return null;
    return current.monthly ?? current.availablePackages[0] ?? null;
  } catch (e) {
    console.error('RevenueCat getOfferings failed:', e);
    return null;
  }
}

/** Buy Pro. Returns true if the entitlement is active afterwards. Throws on real errors (not user-cancel). */
export async function purchasePro(pkg: PurchasesPackage): Promise<boolean> {
  const P = rc();
  if (!P) return false;
  const { customerInfo } = await P.purchasePackage(pkg);
  return hasProEntitlement(customerInfo);
}

/** True if the user cancelled the StoreKit sheet (not a failure to surface). */
export function isUserCancelled(e: any): boolean {
  return Boolean(e?.userCancelled);
}

/** Restore prior purchases (required by App Store). Returns true if Pro is active. */
export async function restorePro(): Promise<boolean> {
  const P = rc();
  if (!P) return false;
  try {
    const info = await P.restorePurchases();
    return hasProEntitlement(info);
  } catch (e) {
    console.error('RevenueCat restore failed:', e);
    return false;
  }
}

/** Current entitlement state, straight from StoreKit. */
export async function isProActive(): Promise<boolean> {
  const P = rc();
  if (!P) return false;
  try {
    const info = await P.getCustomerInfo();
    return hasProEntitlement(info);
  } catch {
    return false;
  }
}
