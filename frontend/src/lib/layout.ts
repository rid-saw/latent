import type { BlockLayout, SourceKind } from "@/types";

// Default block size per content type. Video blocks need room for big 16:9
// thumbnails; link-preview content (articles, email, news) is more compact.
// y: Infinity → react-grid-layout appends at the bottom.
const sizes: Record<SourceKind, { w: number; h: number }> = {
  youtube: { w: 4, h: 6 },
  papers: { w: 4, h: 4 },
  news: { w: 4, h: 4 },
  gmail: { w: 3, h: 4 },
  sports: { w: 3, h: 3 },
  web: { w: 4, h: 4 },
};

export function defaultLayout(source: SourceKind): BlockLayout {
  return { x: 0, y: Infinity, ...sizes[source] };
}
