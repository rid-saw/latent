import type { Api } from "./client";
import type { Block, ContentItem, Page, SourceKind } from "@/types";
import { defaultLayout } from "@/lib/layout";

const mockPages: Page[] = [{ id: "default", name: "Home", emoji: "home" }];

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

function inferSource(q: string): SourceKind {
  const s = q.toLowerCase();
  if (/https?:\/\/|www\./.test(s)) return "site";
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
  const id = crypto.randomUUID();
  return {
    id,
    title: `Latest on "${titleFrom(query)}"`,
    url: "https://example.com",
    source,
    summary:
      "Mock result — the agent will replace this with a real, ranked item once the backend is wired.",
    meta: source === "youtube" ? "Channel · just now" : "Source · just now",
    thumbnail: `https://picsum.photos/seed/${id.slice(0, 8)}/640/360`,
  };
}

const seed: Block[] = [
  {
    id: "seed-papers",
    page_id: "default",
    title: "Recent papers on AI + medicine",
    query: "recent high-impact papers on AI and medicine",
    source: "papers",
    layout: { x: 0, y: 0, w: 6, h: 7 },
    status: "ready",
    max_items: 3,
    items: [
      {
        id: "p1",
        title: "Foundation models for clinical decision support",
        url: "https://example.com",
        source: "papers",
        meta: "Nature Medicine · 2d ago",
        summary: "Survey of LLM-based diagnostics with a new benchmark.",
        thumbnail: "https://picsum.photos/seed/natmed1/640/360",
      },
      {
        id: "p2",
        title: "Multimodal transformers for radiology report generation",
        url: "https://example.com",
        source: "papers",
        meta: "arXiv · 8h ago",
        summary: "SOTA on MIMIC-CXR with a fraction of the parameters.",
        thumbnail: "https://picsum.photos/seed/arxiv2/640/360",
      },
    ],
  },
  {
    id: "seed-yt",
    page_id: "default",
    title: "AI research channels",
    query: "new videos from AI research youtube channels",
    source: "youtube",
    layout: { x: 6, y: 0, w: 4, h: 6 },
    status: "ready",
    max_items: 3,
    items: [
      {
        id: "y1",
        title: "What actually changed in transformers this year",
        url: "https://example.com",
        source: "youtube",
        meta: "Yannic Kilcher · 1d ago",
        thumbnail: "https://picsum.photos/seed/yt1/640/360",
      },
      {
        id: "y2",
        title: "Building agents that don't fall over: lessons from prod",
        url: "https://example.com",
        source: "youtube",
        meta: "AI Engineer · 3d ago",
        thumbnail: "https://picsum.photos/seed/yt2/640/360",
      },
    ],
  },
];

export const mockApi: Api = {
  async listPages() {
    await delay(100);
    return mockPages.map((p) => ({ ...p }));
  },
  async createPage(name, emoji) {
    await delay(150);
    const page = { id: crypto.randomUUID(), name, emoji };
    mockPages.push(page);
    return { ...page };
  },
  async deletePage(id) {
    await delay(100);
    const i = mockPages.findIndex((p) => p.id === id);
    if (i >= 0) mockPages.splice(i, 1);
  },
  async listBlocks(pageId) {
    await delay(150);
    return seed.filter((b) => b.page_id === pageId).map((b) => ({ ...b }));
  },
  async createBlock(query, pageId) {
    await delay(600);
    const source = inferSource(query);
    return {
      id: crypto.randomUUID(),
      page_id: pageId,
      title: titleFrom(query),
      query,
      source,
      layout: defaultLayout(source),
      status: "ready",
      items: [fakeItem(query, source)],
      max_items: 3,
    };
  },
  async refreshBlock(block) {
    await delay(500);
    return { ...block, status: "ready", items: [fakeItem(block.query, block.source)] };
  },
  async deleteBlock() {
    await delay(100);
  },
  async saveLayouts() {
    // no-op in mock mode
  },
  async getRundown() {
    await delay(150);
    return null;
  },
  async generateRundown() {
    await delay(1500);
    return {
      id: crypto.randomUUID(),
      text: "Mock rundown — 3 new med-AI papers today, the Nature one on clinical LLMs is the standout. Your inbox has 2 newsletters worth opening; the rest is noise.",
      created_at: new Date().toISOString(),
    };
  },
};
