import type { BlockLayout, SourceKind } from "@/types";

// Default block size per content type. Video blocks need room for big 16:9
// thumbnails; link-preview content (articles, email, news) is more compact.
// y: Infinity → react-grid-layout appends at the bottom.
const sizes: Record<SourceKind, { w: number; h: number }> = {
  youtube: { w: 4, h: 6 },
  papers: { w: 6, h: 7 },
  news: { w: 4, h: 4 },
  gmail: { w: 3, h: 4 },
  sports: { w: 3, h: 3 },
  web: { w: 4, h: 4 },
};

export function defaultLayout(source: SourceKind): BlockLayout {
  return { x: 0, y: Infinity, ...sizes[source] };
}

export const intersects = (a: BlockLayout, b: BlockLayout) =>
  a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;

/** First free spot scanning like reading order: left→right, then next row. */
export function findSpot(
  w: number,
  h: number,
  occupied: BlockLayout[],
  cols = 12,
): { x: number; y: number } {
  for (let y = 0; ; y++) {
    for (let x = 0; x <= cols - w; x++) {
      const cand = { x, y, w, h };
      if (!occupied.some((o) => intersects(cand, o))) return { x, y };
    }
  }
}
