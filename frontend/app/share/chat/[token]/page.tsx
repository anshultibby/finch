import { cache } from 'react';
import type { Metadata } from 'next';
import SharedChatView from './SharedChatView';
import type { SharedChat } from '@/lib/types';

// Server component: fetching here (instead of in the client) lets us emit real
// OG/Twitter meta tags, so shared links unfurl with the chat title in
// WhatsApp/iMessage/Twitter instead of the generic site card.

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const getSharedChat = cache(async (token: string): Promise<SharedChat | null> => {
  try {
    const res = await fetch(`${API_BASE_URL}/chat/shared/${encodeURIComponent(token)}`, {
      cache: 'no-store',
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
});

export async function generateMetadata(
  { params }: { params: Promise<{ token: string }> }
): Promise<Metadata> {
  const { token } = await params;
  const chat = await getSharedChat(token);
  if (!chat) {
    return { title: 'Shared analysis — Finch', robots: { index: false } };
  }
  const title = chat.title || 'Shared analysis';
  const firstUserMessage = chat.messages.find((m) => m.role === 'user')?.content?.trim();
  const description = (firstUserMessage || 'AI market and portfolio analysis, made with Finch.')
    .replace(/\s+/g, ' ')
    .slice(0, 160);
  return {
    title: `${title} — Finch`,
    description,
    openGraph: {
      title,
      description,
      siteName: 'Finch',
      type: 'article',
      images: ['/logo.png'],
    },
    twitter: {
      card: 'summary',
      title,
      description,
      images: ['/logo.png'],
    },
  };
}

export default async function SharedChatPage(
  { params }: { params: Promise<{ token: string }> }
) {
  const { token } = await params;
  const chat = await getSharedChat(token);
  return <SharedChatView chat={chat} token={token} />;
}
