// The contract. Frontend renders against this; the backend fills it.
// Keep in sync with backend/app/models/schemas.py.

export type SourceKind =
  | "youtube"
  | "gmail"
  | "papers"
  | "news"
  | "sports"
  | "jobs"
  | "web"
  | "site";

/** How a block's answer is laid out. Only web varies: every other source
 *  returns things that already are pages, so "links" is all that fits them. */
export type BlockFormat =
  | "links"
  | "text"
  | "bullets"
  | "steps"
  | "table"
  | "stat"
  | "code";

export interface ContentItem {
  id: string;
  title: string;
  /** The page this came from. Empty when the item is a thing rather than a
   *  page — a sale, a fact, a slang term — so cards must not assume a link. */
  url: string;
  source: SourceKind;
  summary?: string;
  meta?: string; // e.g. "Nature · 2d ago" or a channel name
  thumbnail?: string;
  /** Named values about this item: {price: "A$2.4M", citations: "514"}.
   *  Insertion order is the display order the backend chose. */
  fields?: Record<string, string>;
  /** The answer itself when it's longer than a title — the prose of an
   *  explanation, the lines of a snippet. */
  body?: string;
}

export interface BlockLayout {
  x: number;
  y: number;
  w: number;
  h: number;
}

export type BlockStatus = "idle" | "loading" | "ready" | "error";

export interface Page {
  id: string;
  name: string;
  emoji: string;
}

/** The agent's answers about one block. Stored whole rather than split into
 *  named columns, because every decision that lacked one was dropped on the
 *  first refresh — a channel block reverting to a web search, a table
 *  reverting to links. */
export interface BlockPlan {
  search_terms?: string;
  format?: BlockFormat;
  fields?: string[];
  channel?: string;
  location?: string;
  wants_latest?: boolean;
  max_items?: number;
  [key: string]: unknown;
}

export interface Block {
  id: string;
  page_id: string;
  title: string;
  query: string; // the natural-language prompt the user typed
  /** Everything the agent decided, kept whole: what it searched for, how many
   *  items, and whichever of channel / location / format / fields apply.
   *  An empty plan means routing never finished, so retrying has to re-run the
   *  agent rather than refetch. */
  plan?: BlockPlan;
  source: SourceKind;
  layout: BlockLayout;
  items: ContentItem[];
  status: BlockStatus;
  max_items: number; // how many items to show (user can specify in the prompt)
}

export interface Briefing {
  id: string;
  text: string;
  created_at: string;
}
