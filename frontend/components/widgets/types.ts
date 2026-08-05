// Widget spec + data-shape types. Mirrors backend/schemas/widget.py and the
// data shapes in services/widget_data.py. See docs/widgets/spec.md.

export type TileType = 'chart' | 'stat' | 'odds' | 'news' | 'table' | 'text';
export type TileSize = 'sm' | 'md' | 'lg' | 'full';

export interface Tile {
  id: string;
  type: TileType;
  title?: string;
  size?: TileSize;
  query: Record<string, any>;
  transforms?: Record<string, any>[];
  options?: Record<string, any>;
}

export interface WidgetSpec {
  spec_version: number;
  tiles: Tile[];
  refresh?: { interval_seconds: number };
}

export interface Widget {
  id: string;
  user_id: string;
  title: string;
  description?: string | null;
  emoji?: string | null;
  tags?: string[] | null;
  spec: WidgetSpec;
  visibility: 'private' | 'public';
  slug?: string | null;
  cloned_from?: string | null;
  view_count: number;
  clone_count: number;
  is_owner: boolean;
  created_at: string;
  updated_at: string;
}

export interface WidgetSummary {
  id: string;
  title: string;
  description?: string | null;
  emoji?: string | null;
  tags?: string[] | null;
  visibility: 'private' | 'public';
  slug?: string | null;
  view_count: number;
  clone_count: number;
  created_at: string;
}

export interface PublicWidget {
  id: string;
  slug: string;
  title: string;
  description?: string | null;
  emoji?: string | null;
  tags?: string[] | null;
  spec: WidgetSpec;
  view_count: number;
  clone_count: number;
}

// ── data shapes (returned by /data and /shared/{slug}/data) ────────────────
export interface SeriesPoint { t: string; v: number | null }
export interface SeriesData {
  shape: 'series';
  series: { label: string; points: SeriesPoint[] }[];
  asof?: string;
}
export interface TableData {
  shape: 'table';
  columns: string[];
  rows: (string | number | null)[][];
  asof?: string;
}
export interface NumberData {
  shape: 'number';
  label?: string;
  value: number | null;
  delta?: number | null;
  delta_pct?: number | null;
  sparkline?: number[];
  asof?: string;
}
export interface OddsData {
  shape: 'odds';
  prob: number | null;
  title?: string;
  close_date?: string | null;
  history?: SeriesPoint[];
  asof?: string;
}
export interface NewsData {
  shape: 'news';
  items: { title: string; url?: string; source?: string; published_at?: string; image?: string }[];
  asof?: string;
}
export interface MarkdownData { shape: 'markdown'; text: string; asof?: string }
export interface EmptyData { shape: 'empty'; reason: string }
export interface ErrorData { shape: 'error'; message: string }

export type TileData =
  | SeriesData | TableData | NumberData | OddsData
  | NewsData | MarkdownData | EmptyData | ErrorData;

export type WidgetData = Record<string, TileData>;
