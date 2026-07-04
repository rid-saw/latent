import type { Block, BlockLayout, SourceKind } from "@/types";

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

/** One-time gravity: slide each block up as far as free space allows (x kept).
 * Used after deletions so neighbors fill the vacated space. */
export function compactUp(blocks: Block[]): {
  blocks: Block[];
  changed: Record<string, BlockLayout>;
} {
  const sorted = [...blocks].sort(
    (a, b) => a.layout.y - b.layout.y || a.layout.x - b.layout.x,
  );
  const placed: BlockLayout[] = [];
  const changed: Record<string, BlockLayout> = {};
  const out = sorted.map((b) => {
    let y = b.layout.y;
    for (let candY = 0; candY < b.layout.y; candY++) {
      if (!placed.some((o) => intersects({ ...b.layout, y: candY }, o))) {
        y = candY;
        break;
      }
    }
    const layout = { ...b.layout, y };
    placed.push(layout);
    if (y !== b.layout.y) changed[b.id] = layout;
    return { ...b, layout };
  });
  return { blocks: out, changed };
}

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
