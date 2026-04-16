import { NextRequest, NextResponse } from 'next/server';

// Server-side proxy to Yahoo Finance — avoids CORS and needs no API key
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const symbols = searchParams.get('symbols') || '';
  const days = parseInt(searchParams.get('days') || '365', 10);

  const tickers = symbols.split(',').map(s => s.trim().toUpperCase()).filter(Boolean);
  if (!tickers.length || tickers.length > 5) {
    return NextResponse.json({ error: 'Provide 1–5 symbols' }, { status: 400 });
  }

  const range = days >= 1000 ? 'max' : days >= 300 ? '1y' : days >= 150 ? '6mo' : days >= 60 ? '3mo' : '1mo';
  const result: Record<string, { date: string; pct: number }[]> = {};

  await Promise.all(tickers.map(async (symbol) => {
    try {
      const url = `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?interval=1d&range=${range}`;
      const res = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0' }, next: { revalidate: 3600 } });
      if (!res.ok) { result[symbol] = []; return; }

      const data = await res.json();
      const chartResult = data?.chart?.result?.[0];
      if (!chartResult) { result[symbol] = []; return; }

      const timestamps: number[] = chartResult.timestamp ?? [];
      const closes: (number | null)[] = chartResult.indicators?.adjclose?.[0]?.adjclose
        ?? chartResult.indicators?.quote?.[0]?.close
        ?? [];

      const rows: { date: string; close: number }[] = [];
      for (let i = 0; i < timestamps.length; i++) {
        const c = closes[i];
        if (c == null) continue;
        const d = new Date(timestamps[i] * 1000);
        rows.push({ date: d.toISOString().split('T')[0], close: c });
      }

      if (!rows.length) { result[symbol] = []; return; }
      const base = rows[0].close;
      result[symbol] = rows.map(r => ({ date: r.date, pct: Math.round((r.close / base - 1) * 1000) / 10 }));
    } catch {
      result[symbol] = [];
    }
  }));

  return NextResponse.json(result);
}
