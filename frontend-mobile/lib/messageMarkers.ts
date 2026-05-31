// Parses inline markers the agent embeds in assistant message text.
// Currently handles visualization references, e.g. `{{visualization:chart.html}}`
// (and the legacy `[visualization: chart.html]` form), splitting a message into
// renderable text segments and visualization chips.

export type MessagePart =
  | { type: 'text'; value: string }
  | { type: 'visualization'; filename: string };

// Group 1 = {{visualization:...}}, group 2 = [visualization: ...]
// Empty markers are matched (so they're consumed) but dropped below.
const VIZ_MARKER = /\{\{visualization:([^}]*)\}\}|\[visualization:\s*([^\]]*)\]/g;

export function parseMessageParts(content: string): MessagePart[] {
  if (!content) return [];

  const parts: MessagePart[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  VIZ_MARKER.lastIndex = 0;

  while ((match = VIZ_MARKER.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: 'text', value: content.slice(lastIndex, match.index) });
    }
    const filename = (match[1] || match[2] || '').trim();
    if (filename) parts.push({ type: 'visualization', filename });
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < content.length) {
    parts.push({ type: 'text', value: content.slice(lastIndex) });
  }

  // Drop whitespace-only text fragments left behind by markers on their own line.
  return parts.filter((p) => p.type !== 'text' || p.value.trim().length > 0);
}

export function hasVisualization(content: string): boolean {
  if (!content) return false;
  VIZ_MARKER.lastIndex = 0;
  return VIZ_MARKER.test(content);
}
