// Client-side reconstruction of the AI trading agent's performance.
//
// Robinhood's MCP exposes no portfolio-value history, so we rebuild an equity
// curve from two things we *do* have: the agent's filled orders (what it held,
// when) and real historical prices. The price endpoint (/api/market-prices)
// returns % change vs a pre-window anchor close — not absolute prices — so we
// recover absolute prices per symbol from a known anchor (current last price for
// held names; the last fill price for fully-closed names).
//
// Assumptions (documented so the curve is read honestly):
//  - No cash deposits/withdrawals within the window. True for a single-funded
//    agent account; a mid-window transfer would shift the curve by that amount.
//  - Reconstruction only reaches as far back as the fills we fetched (deep but
//    finite). Before the earliest fill, share counts are clamped to ≥ 0.
//  - Symbols whose price series is unavailable are omitted from invested value.

import type { ChartMarker, SeriesPoint } from '@/components/ui/PriceRangeChart';
import type { RobinhoodHolding, RobinhoodOrder } from '@/lib/api';

export interface RawPoint {
  date: string;
  pct: number;
}

const MARKET_PRICES_CHUNK = 5; // /market/prices accepts at most 5 symbols per call.

const num = (v: unknown): number => {
  const n = typeof v === 'number' ? v : parseFloat(String(v ?? ''));
  return Number.isFinite(n) ? n : 0;
};

const ms = (iso?: string): number => {
  if (!iso) return 0;
  const t = new Date(iso).getTime();
  return Number.isFinite(t) ? t : 0;
};

/**
 * Fetch % -change price series for many symbols, batched to the endpoint's
 * 5-symbol limit. Returns a merged { SYMBOL: RawPoint[] } map.
 */
export async function fetchPriceSeries(
  symbols: string[],
  days: number,
): Promise<Record<string, RawPoint[]>> {
  const unique = Array.from(new Set(symbols.map((s) => s.toUpperCase()).filter(Boolean)));
  if (unique.length === 0) return {};

  const chunks: string[][] = [];
  for (let i = 0; i < unique.length; i += MARKET_PRICES_CHUNK) {
    chunks.push(unique.slice(i, i + MARKET_PRICES_CHUNK));
  }

  const results = await Promise.all(
    chunks.map((chunk) =>
      fetch(`/api/market-prices?symbols=${chunk.join(',')}&days=${days}`)
        .then((r) => (r.ok ? r.json() : {}))
        .catch(() => ({})),
    ),
  );

  const merged: Record<string, RawPoint[]> = {};
  for (const res of results) {
    for (const [sym, pts] of Object.entries(res || {})) {
      if (Array.isArray(pts)) merged[sym.toUpperCase()] = pts as RawPoint[];
    }
  }
  return merged;
}

// Index of the series point whose timestamp is closest to `targetMs`.
function nearestIdx(series: RawPoint[], targetMs: number): number {
  let best = 0;
  let bestDist = Infinity;
  for (let i = 0; i < series.length; i++) {
    const d = Math.abs(ms(series[i].date) - targetMs);
    if (d < bestDist) {
      bestDist = d;
      best = i;
    }
  }
  return best;
}

interface CurveInput {
  holdings: RobinhoodHolding[];
  orders: RobinhoodOrder[];
  buyingPower: number;
  pricesBySymbol: Record<string, RawPoint[]>;
}

/**
 * Rebuild portfolio value over time:
 *   value(t) = Σ_sym qtyHeld(sym, t) · price(sym, t) + cash(t)
 *
 * The newest point lands at ≈ current total value (invested + cash) by
 * construction, so the curve's right edge matches the live headline.
 */
export function buildEquityCurve({
  holdings,
  orders,
  buyingPower,
  pricesBySymbol,
}: CurveInput): SeriesPoint[] {
  const heldQty = new Map<string, number>();
  for (const h of holdings) heldQty.set(h.symbol.toUpperCase(), num(h.quantity));

  // Per-symbol absolute-price recovery: base = anchorPrice / (1 + anchorPct/100),
  // then price(idx) = base · (1 + pct(idx)/100).
  const baseBySymbol = new Map<string, number>();
  for (const [sym, series] of Object.entries(pricesBySymbol)) {
    if (!series || series.length === 0) continue;
    const held = holdings.find((h) => h.symbol.toUpperCase() === sym);
    let anchorPrice: number;
    let anchorIdx: number;
    if (held && num(held.last_price) > 0) {
      anchorPrice = num(held.last_price);
      anchorIdx = series.length - 1; // last point ≈ now
    } else {
      // Closed name: anchor on its most recent fill price + nearest series point.
      const fills = orders
        .filter((o) => o.symbol.toUpperCase() === sym && num(o.price) > 0)
        .sort((a, b) => ms(b.at) - ms(a.at));
      if (fills.length === 0) continue;
      anchorPrice = num(fills[0].price);
      anchorIdx = nearestIdx(series, ms(fills[0].at));
    }
    const base = anchorPrice / (1 + num(series[anchorIdx].pct) / 100);
    if (Number.isFinite(base) && base > 0) baseBySymbol.set(sym, base);
  }

  const priceAt = (sym: string, idx: number): number => {
    const base = baseBySymbol.get(sym);
    const series = pricesBySymbol[sym];
    if (base == null || !series || !series[idx]) return 0;
    return base * (1 + num(series[idx].pct) / 100);
  };

  // Build the common time axis from the union of every symbol's dates. FMP daily
  // series share a trading calendar, so we forward-fill each symbol's price into
  // any axis date it's missing.
  const axisSet = new Set<string>();
  for (const series of Object.values(pricesBySymbol)) {
    for (const p of series || []) axisSet.add(p.date);
  }
  const axis = Array.from(axisSet).sort((a, b) => ms(a) - ms(b));
  if (axis.length < 2) return [];

  // For forward-fill: per symbol, map axis date -> price (carry last known).
  const priceByDate = new Map<string, Map<string, number>>(); // sym -> (date -> price)
  for (const sym of Array.from(baseBySymbol.keys())) {
    const series = pricesBySymbol[sym] || [];
    const byDate = new Map<string, number>();
    let si = 0;
    let last = 0;
    for (const d of axis) {
      while (si < series.length && ms(series[si].date) <= ms(d)) {
        last = priceAt(sym, si);
        si++;
      }
      byDate.set(d, last);
    }
    priceByDate.set(sym, byDate);
  }

  // Signed events for share-count + cash reconstruction.
  const events = orders
    .map((o) => ({
      t: ms(o.at),
      sym: o.symbol.toUpperCase(),
      buy: o.side === 'buy',
      qty: num(o.quantity),
      cost: num(o.quantity) * num(o.price),
    }))
    .filter((e) => e.t > 0 && e.qty > 0)
    .sort((a, b) => b.t - a.t); // newest first

  const symbols = Array.from(baseBySymbol.keys());

  const curve: SeriesPoint[] = axis.map((date) => {
    const tMs = ms(date);
    // qtyHeld(sym, t) = currentQty − Σ buys after t + Σ sells after t (clamp ≥ 0)
    const qty = new Map<string, number>(symbols.map((s) => [s, heldQty.get(s) ?? 0]));
    let cash = buyingPower;
    for (const e of events) {
      if (e.t <= tMs) break; // events are newest-first; rest are at/before t
      if (e.buy) {
        qty.set(e.sym, (qty.get(e.sym) ?? 0) - e.qty);
        cash += e.cost; // cash was higher before this buy spent it
      } else {
        qty.set(e.sym, (qty.get(e.sym) ?? 0) + e.qty);
        cash -= e.cost; // cash was lower before this sale added to it
      }
    }
    let invested = 0;
    for (const sym of symbols) {
      const q = Math.max(0, qty.get(sym) ?? 0);
      if (q > 0) invested += q * (priceByDate.get(sym)?.get(date) ?? 0);
    }
    return { date, value: Math.max(0, invested + cash) };
  });

  return curve;
}

export interface RealizedStats {
  realizedPnl: number;
  closedTrades: number;
  winRate: number; // 0..1
  bestTrade: { symbol: string; pnl: number } | null;
  worstTrade: { symbol: string; pnl: number } | null;
}

/**
 * FIFO-match buys → sells per symbol to derive realized P&L and win stats.
 * Each closing sell counts as one "trade" for win-rate purposes.
 */
export function reconstructRealizedStats(orders: RobinhoodOrder[]): RealizedStats {
  const bySymbol = new Map<string, RobinhoodOrder[]>();
  for (const o of orders) {
    const sym = o.symbol.toUpperCase();
    if (!bySymbol.has(sym)) bySymbol.set(sym, []);
    bySymbol.get(sym)!.push(o);
  }

  let realizedPnl = 0;
  let closedTrades = 0;
  let wins = 0;
  let bestTrade: RealizedStats['bestTrade'] = null;
  let worstTrade: RealizedStats['worstTrade'] = null;

  for (const [sym, list] of Array.from(bySymbol)) {
    const sorted = [...list].sort((a, b) => ms(a.at) - ms(b.at));
    const lots: { qty: number; price: number }[] = []; // FIFO buy lots
    for (const o of sorted) {
      const qty = num(o.quantity);
      const price = num(o.price);
      if (qty <= 0) continue;
      if (o.side === 'buy') {
        lots.push({ qty, price });
        continue;
      }
      // Sell: match against oldest lots.
      let remaining = qty;
      let pnl = 0;
      while (remaining > 0 && lots.length > 0) {
        const lot = lots[0];
        const matched = Math.min(remaining, lot.qty);
        pnl += matched * (price - lot.price);
        lot.qty -= matched;
        remaining -= matched;
        if (lot.qty <= 1e-9) lots.shift();
      }
      // Only count as a closed trade if we actually matched against a buy lot.
      if (remaining < qty) {
        realizedPnl += pnl;
        closedTrades += 1;
        if (pnl > 0) wins += 1;
        if (!bestTrade || pnl > bestTrade.pnl) bestTrade = { symbol: sym, pnl };
        if (!worstTrade || pnl < worstTrade.pnl) worstTrade = { symbol: sym, pnl };
      }
    }
  }

  return {
    realizedPnl,
    closedTrades,
    winRate: closedTrades > 0 ? wins / closedTrades : 0,
    bestTrade,
    worstTrade,
  };
}

/** Buy/sell arrows for the equity chart, at the times the agent traded. */
export function ordersToMarkers(orders: RobinhoodOrder[]): ChartMarker[] {
  return orders
    .filter((o) => o.at)
    .map((o) => {
      const isSell = o.side === 'sell';
      return {
        time: o.at,
        position: isSell ? 'aboveBar' : 'belowBar',
        color: isSell ? '#ef4444' : '#10b981',
        shape: isSell ? 'arrowDown' : 'arrowUp',
        text: o.symbol,
      } as ChartMarker;
    });
}

/** Agent's % return over the window from the reconstructed curve. */
export function periodReturnPct(curve: SeriesPoint[]): number | null {
  if (curve.length < 2) return null;
  const start = curve[0].value;
  const end = curve[curve.length - 1].value;
  if (start <= 0) return null;
  return (end / start - 1) * 100;
}

/** S&P benchmark % over the same window = the SPY series' last anchored pct. */
export function benchmarkReturnPct(spySeries: RawPoint[] | undefined): number | null {
  if (!spySeries || spySeries.length === 0) return null;
  return num(spySeries[spySeries.length - 1].pct);
}
