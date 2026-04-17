import { NextRequest, NextResponse } from 'next/server';

// Proxies to the backend /market/prices endpoint, which uses FMP (with caching).
// Backend handles intraday bars for short windows and anchors the % baseline to the
// prior close so the 1D chart matches the "Today +X%" shown in the quote header.
const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const symbols = searchParams.get('symbols') || '';
  const days = searchParams.get('days') || '365';
  const intraday = parseInt(days, 10) <= 7;

  try {
    const url = `${BACKEND_URL}/market/prices?symbols=${encodeURIComponent(symbols)}&days=${encodeURIComponent(days)}`;
    const res = await fetch(url, { next: { revalidate: intraday ? 60 : 3600 } });
    if (!res.ok) {
      return NextResponse.json({ error: 'upstream failed' }, { status: res.status });
    }
    return NextResponse.json(await res.json());
  } catch {
    return NextResponse.json({});
  }
}
