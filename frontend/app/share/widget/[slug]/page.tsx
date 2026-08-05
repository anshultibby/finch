import { cache } from 'react';
import type { Metadata } from 'next';
import SharedWidgetView from './SharedWidgetView';
import type { PublicWidget } from '@/components/widgets/types';

// Server component: fetch here so we emit real OG/Twitter tags and the
// file-based opengraph-image.tsx renders per-widget. This is the Reddit/Slack
// link-preview surface, so it matters.

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const getSharedWidget = cache(async (slug: string): Promise<PublicWidget | null> => {
  try {
    const res = await fetch(`${API_BASE_URL}/widgets/shared/${encodeURIComponent(slug)}`, {
      cache: 'no-store',
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
});

export async function generateMetadata(
  { params }: { params: Promise<{ slug: string }> }
): Promise<Metadata> {
  const { slug } = await params;
  const widget = await getSharedWidget(slug);
  if (!widget) {
    return { title: 'Widget — Finch', robots: { index: false } };
  }
  const title = `${widget.emoji ? widget.emoji + ' ' : ''}${widget.title}`;
  const description = (widget.description || 'A live financial widget, made with Finch.')
    .replace(/\s+/g, ' ')
    .slice(0, 160);
  // NOTE: intentionally not setting openGraph.images — the file-based
  // opengraph-image.tsx in this folder provides the per-widget card.
  return {
    title: `${widget.title} — Finch`,
    description,
    openGraph: { title, description, siteName: 'Finch', type: 'website' },
    twitter: { card: 'summary_large_image', title, description },
  };
}

export default async function SharedWidgetPage(
  { params }: { params: Promise<{ slug: string }> }
) {
  const { slug } = await params;
  const widget = await getSharedWidget(slug);
  return <SharedWidgetView widget={widget} slug={slug} />;
}
