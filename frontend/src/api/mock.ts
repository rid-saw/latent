import type { Api } from "./client";
import type { Block, ContentItem, SourceKind } from "@/types";

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

function inferSource(q: string): SourceKind {
  const s = q.toLowerCase();
  if (/(paper|arxiv|research|study|journal)/.test(s)) return "papers";
  if (/(youtube|video|channel)/.test(s)) return "youtube";
  if (/(email|inbox|newsletter|gmail)/.test(s)) return "gmail";
  if (/(sport|nba|nfl|soccer|football|match)/.test(s)) return "sports";
  if (/(news|headline)/.test(s)) return "news";
  return "web";
}

function titleFrom(q: string): string {
  const t = q.trim();
  if (!t) return "New block";
  return t.length > 42 ? t.slice(0, 42) + "…" : t;
}

function fakeItem(query: string, source: SourceKind): ContentItem {
  return {
    id: crypto.randomUUID(),
    title: `Latest on "${titleFrom(query)}"`,
    url: "https://example.com",
    source,
    summary:
      "Mock result — the agent will replace this with a real, ranked item once the backend is wired.",
    meta: "Source · just now",
  };
}

const seed: Block[] = [
  {
    id: "seed-papers",
    title: "Recent papers on AI + medicine",
    query: "recent high-impact papers on AI and medicine",
    source: "papers",
    layout: { x: 0, y: 0, w: 4, h: 4 },
    status: "ready",
    items: [
      {
        id: "p1",
        title: "Foundation models for clinical decision support",
        url: "https://example.com",
        source: "papers",
        meta: "Nature Medicine · 2d ago",
        summary: "Survey of LLM-based diagnostics with a new benchmark.",
      },
    ],
  },
  {
    id: "seed-yt",
    title: "AI research channels",
    query: "new videos from AI research youtube channels",
    source: "youtube",
    layout: { x: 4, y: 0, w: 4, h: 4 },
    status: "ready",
    items: [
      {
        id: "y1",
        title: "What actually changed in transformers this year",
        url: "https://example.com",
        source: "youtube",
        meta: "Yannic Kilcher · 1d ago",
      },
    ],
  },
];

export const mockApi: Api = {
  async listBlocks() {
    await delay(150);
    return seed.map((b) => ({ ...b }));
  },
  async createBlock(query) {
    await delay(600);
    const source = inferSource(query);
    return {
      id: crypto.randomUUID(),
      title: titleFrom(query),
      query,
      source,
      layout: { x: 0, y: Infinity, w: 4, h: 4 },
      status: "ready",
      items: [fakeItem(query, source)],
    };
  },
  async refreshBlock(block) {
    await delay(500);
    return { ...block, status: "ready", items: [fakeItem(block.query, block.source)] };
  },
  async deleteBlock() {
    await delay(100);
  },
};
