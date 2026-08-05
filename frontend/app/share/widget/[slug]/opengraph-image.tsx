import { ImageResponse } from 'next/og';

// Per-widget OG card for link unfurls (Reddit/Slack/Twitter). Self-contained —
// no external assets (CSP/edge-safe).
export const runtime = 'edge';
export const alt = 'Finch widget';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default async function Image({ params }: { params: { slug: string } }) {
  let widget: any = null;
  try {
    const res = await fetch(`${API_BASE_URL}/widgets/shared/${encodeURIComponent(params.slug)}`, {
      cache: 'no-store',
    });
    if (res.ok) widget = await res.json();
  } catch {
    /* fall through to generic card */
  }

  const emoji = widget?.emoji || '📊';
  const title = widget?.title || 'Finch widget';
  const description = (widget?.description || 'A live financial widget, made with Finch.').slice(0, 120);
  const tags: string[] = (widget?.tags || []).slice(0, 4);

  return new ImageResponse(
    (
      <div
        style={{
          height: '100%',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          background: '#fafaf9',
          padding: '72px',
          fontFamily: 'sans-serif',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <div style={{ fontSize: 120, lineHeight: 1 }}>{emoji}</div>
          <div style={{ fontSize: 64, fontWeight: 700, color: '#1c1917', marginTop: 28, maxWidth: 1000 }}>
            {title}
          </div>
          <div style={{ fontSize: 30, color: '#57534e', marginTop: 20, maxWidth: 900 }}>
            {description}
          </div>
          <div style={{ display: 'flex', gap: 12, marginTop: 28 }}>
            {tags.map((t) => (
              <div
                key={t}
                style={{
                  fontSize: 22,
                  color: '#047857',
                  background: '#ecfdf5',
                  border: '2px solid #a7f3d0',
                  borderRadius: 999,
                  padding: '6px 20px',
                }}
              >
                {t}
              </div>
            ))}
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{ width: 44, height: 44, borderRadius: 12, background: '#10b981' }} />
            <div style={{ fontSize: 32, fontWeight: 600, color: '#1c1917' }}>Finch</div>
          </div>
          <div style={{ fontSize: 26, color: '#10b981', fontWeight: 600 }}>● Live · refreshes automatically</div>
        </div>
      </div>
    ),
    { ...size }
  );
}
