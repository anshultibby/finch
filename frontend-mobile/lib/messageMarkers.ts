// The visualizations subsystem was replaced by Widgets (Aug 2026), so the agent
// no longer emits inline `{{visualization:...}}` markers. Old chat history may
// still contain them — strip any leftovers so they don't render as raw text.

const LEGACY_VIZ_MARKER = /\{\{visualization:[^}]*\}\}|\[visualization:\s*[^\]]*\]/g;

export function stripLegacyMarkers(content: string): string {
  if (!content) return '';
  return content.replace(LEGACY_VIZ_MARKER, '').replace(/\n{3,}/g, '\n\n');
}
