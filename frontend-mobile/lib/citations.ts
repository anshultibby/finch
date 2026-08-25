// Citation parsing for chat messages — mobile port of the web logic.
// A source may be a web link (bare url or markdown link) or, for fetched/computed
// data (FMP, get_equity_quotes, "Calculated from …"), a plain text label with no
// url. Both must render — dropping the label-only case is what left the Sources
// list empty on data-heavy analyses.

export type Citation = { url?: string; label?: string };

export function extractCitations(md: string): Map<number, Citation> {
  const refs = new Map<number, Citation>();
  const linked = /\[\^(\d+)\]\((https?:\/\/[^)]+)\)/g;
  let m: RegExpExecArray | null;
  while ((m = linked.exec(md)) !== null) {
    refs.set(parseInt(m[1]), { url: m[2] });
  }
  const defs = /^\[\^(\d+)\]:\s*(.+?)\s*$/gm;
  while ((m = defs.exec(md)) !== null) {
    const n = parseInt(m[1]);
    if (refs.has(n)) continue;
    const rest = m[2].trim();
    const mdLink = rest.match(/\[([^\]]*)\]\((https?:\/\/[^)\s]+)\)/);
    const bareUrl = rest.match(/(https?:\/\/[^)\s]+)/);
    if (mdLink) {
      refs.set(n, { url: mdLink[2], label: mdLink[1].trim() || undefined });
    } else if (bareUrl) {
      const label = rest.replace(bareUrl[1], '').replace(/[—–-]\s*$/, '').trim();
      refs.set(n, { url: bareUrl[1], label: label || undefined });
    } else {
      refs.set(n, { label: rest });
    }
  }
  return refs;
}

// Prepare content for react-native-markdown-display. That renderer has no footnote
// support and would print `[^N]` literally, so: turn web citations into a plain
// `[N]` superscript-ish marker (the tappable Sources list below handles opening the
// source), keep `[^N](url)` as a real link, and drop the `[^N]:` definition lines
// (they're rendered as the Sources list instead).
export function preprocessCitationsMobile(md: string): string {
  let r = md.replace(/\[\^(\d+)\]\((https?:\/\/[^)]+)\)/g, (_m, n, url) => `[${n}](${url})`);
  r = r.replace(/\[\^(\d+)\](?![:(])/g, (_m, n) => ` [${n}]`);
  r = r.replace(/^\[\^\d+\]:.*$/gm, '');
  return r.replace(/\n{3,}/g, '\n\n').trim();
}
