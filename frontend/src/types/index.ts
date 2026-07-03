// The contract. Frontend renders against this; the backend fills it.
// Keep in sync with backend/app/models/schemas.py.

export type SourceKind =
  | "youtube"
  | "gmail"
  | "papers"
  | "news"
  | "sports"
  | "web";

export interface ContentItem {
  id: string;
  title: string;
  url: string;
  source: SourceKind;
  summary?: string;
  meta?: string; // e.g. "Nature · 2d ago" or a channel name
  thumbnail?: string;
}

export interface BlockLayout {
  x: number;
  y: number;
  w: number;
  h: number;
}

export type BlockStatus = "idle" | "loading" | "ready" | "error";

export interface Block {
  id: string;
  title: string;
  query: string; // the natural-language prompt the user typed
  source: SourceKind;
  layout: BlockLayout;
  items: ContentItem[];
  status: BlockStatus;
}
