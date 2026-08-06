// Widget spec + data-shape types. Mirrors backend/schemas/widget.py and the
// data shapes in services/widget_data.py. See docs/widgets/spec.md.

export type TileType = 'chart' | 'stat' | 'odds' | 'news' | 'table' | 'text' | 'chart_spec';
export type TileSize = 'sm' | 'md' | 'lg' | 'full';

// Interactive controls — client-side filter/sort/search over a table tile.
export type Control =
  | { id: string; type: 'range'; label: string; column: string; min?: number; max?: number; step?: number }
  | { id: string; type: 'select'; label: string; column: string; options?: string[] }
  | { id: string; type: 'search'; label: string; columns: string[] }
  | { id: string; type: 'sort'; label: string; columns: string[]; default_desc?: boolean };

export interface Tile {
  id: string;
  type: TileType;
  title?: string;
  size?: TileSize;
  query?: Record<string, any>; // optional for self-contained chart_spec tiles
  // Multi-source: named sub-queries merged into one chart (chart/chart_spec).
  queries?: Record<string, { query: Record<string, any>; transforms?: Record<string, any>[] }>;
  transforms?: Record<string, any>[];
  options?: Record<string, any>; // chart_spec: options.figure = Plotly {data, layout}
  controls?: Control[];
}

export interface StaticData { shape: 'static' }
export interface MultiData {
  shape: 'multi';
  parts: Record<string, TileData>;
  source?: DataSource;
  asof?: string;
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
export interface DataSource { label: string; url?: string }
export interface SeriesPoint { t: string; v: number | null }
export interface SeriesData {
  shape: 'series';
  series: { label: string; points: SeriesPoint[] }[];
  source?: DataSource;
  asof?: string;
}
export interface TableData {
  shape: 'table';
  columns: string[];
  rows: (string | number | null)[][];
  source?: DataSource;
  asof?: string;
}
export interface NumberData {
  shape: 'number';
  label?: string;
  value: number | null;
  delta?: number | null;
  delta_pct?: number | null;
  sparkline?: number[];
  source?: DataSource;
  asof?: string;
}
export interface OddsData {
  shape: 'odds';
  prob: number | null;
  title?: string;
  close_date?: string | null;
  history?: SeriesPoint[];
  source?: DataSource;
  asof?: string;
}
export interface NewsData {
  shape: 'news';
  items: { title: string; url?: string; source?: string; published_at?: string; image?: string }[];
  source?: DataSource;
  asof?: string;
}
export interface MarkdownData { shape: 'markdown'; text: string; source?: DataSource; asof?: string }
export interface EmptyData { shape: 'empty'; reason: string }
export interface ErrorData { shape: 'error'; message: string }

export type TileData =
  | SeriesData | TableData | NumberData | OddsData
  | NewsData | MarkdownData | EmptyData | ErrorData | StaticData | MultiData;

export type WidgetData = Record<string, TileData>;
