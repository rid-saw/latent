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
  if (/(jobs?\b|hiring|vacanc|internship|career)/.test(s)) return "jobs";
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

// Demo content. The public demo opens on a populated dashboard — an empty
// grid asks a visitor to do work before the product shows them anything.
// Layouts are in v2 grid units (24 cols, 40px rows).
const seed: Block[] = [
  {
    id: "seed-papers",
    page_id: "default",
    title: "AI in medicine",
    query: "recent high-impact papers on AI and medicine",
    source: "papers",
    layout: { x: 0, y: 0, w: 9, h: 14 },
    status: "ready",
    max_items: 3,
    items: [
      {
        id: "p1",
        title: "Foundation models for clinical decision support",
        url: "https://example.com",
        source: "papers",
        meta: "Nature Medicine \u00b7 2d ago",
        summary: "Survey of LLM-based diagnostics with a new benchmark across 14 hospitals.",
        thumbnail: "https://picsum.photos/seed/natmed1/640/360",
      },
      {
        id: "p2",
        title: "Multimodal transformers for radiology report generation",
        url: "https://example.com",
        source: "papers",
        meta: "arXiv \u00b7 8h ago",
        summary: "State of the art on MIMIC-CXR with a fraction of the parameters.",
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
    layout: { x: 9, y: 0, w: 8, h: 12 },
    status: "ready",
    max_items: 3,
    items: [
      {
        id: "y1",
        title: "What actually changed in transformers this year",
        url: "https://example.com",
        source: "youtube",
        meta: "Yannic Kilcher \u00b7 1d ago",
        thumbnail: "https://picsum.photos/seed/yt1/640/360",
      },
      {
        id: "y2",
        title: "Building agents that don't fall over: lessons from prod",
        url: "https://example.com",
        source: "youtube",
        meta: "AI Engineer \u00b7 3d ago",
        thumbnail: "https://picsum.photos/seed/yt2/640/360",
      },
    ],
  },
  {
    id: "seed-news",
    page_id: "default",
    title: "Semiconductor news",
    query: "latest news on semiconductor supply chains",
    source: "news",
    layout: { x: 17, y: 0, w: 7, h: 12 },
    status: "ready",
    max_items: 3,
    items: [
      {
        id: "n1",
        title: "Fab capacity tightens as advanced packaging demand climbs",
        url: "https://example.com",
        source: "news",
        meta: "Reuters \u00b7 3h ago",
        summary: "Lead times stretch into next year across three major foundries.",
        thumbnail: "https://picsum.photos/seed/news1/640/360",
      },
      {
        id: "n2",
        title: "Export controls reshape memory pricing",
        url: "https://example.com",
        source: "news",
        meta: "Bloomberg \u00b7 9h ago",
        summary: "Contract prices move for the first time in four quarters.",
        thumbnail: "https://picsum.photos/seed/news2/640/360",
      },
    ],
  },
  {
    id: "seed-inbox",
    page_id: "default",
    title: "University mail",
    query: "emails from monash uni",
    plan: { search_terms: "from:monash.edu" },
    source: "gmail",
    layout: { x: 0, y: 14, w: 9, h: 9 },
    status: "ready",
    max_items: 3,
    items: [
      {
        id: "g1",
        title: "Semester 2 enrolment closes Friday",
        url: "https://example.com",
        source: "gmail",
        meta: "Student Services \u00b7 1d ago",
        summary: "Final reminder to finalise your unit selection.",
      },
      {
        id: "g2",
        title: "Guest lecture: interpretability in practice",
        url: "https://example.com",
        source: "gmail",
        meta: "Faculty of IT \u00b7 2d ago",
        summary: "Thursday 4pm, Clayton campus and streamed.",
      },
    ],
  },
  {
    id: "seed-jobs",
    page_id: "default",
    title: "Grad ML roles",
    query: "graduate machine learning jobs in Melbourne",
    plan: { search_terms: "machine learning graduate" },
    source: "jobs",
    layout: { x: 9, y: 12, w: 8, h: 11 },
    status: "ready",
    max_items: 3,
    items: [
      {
        id: "j1",
        title: "Graduate Machine Learning Engineer",
        url: "https://example.com",
        source: "jobs",
        meta: "Melbourne \u00b7 posted 2d ago",
        summary: "Rotational program across recommendations and forecasting.",
      },
      {
        id: "j2",
        title: "Junior Data Scientist",
        url: "https://example.com",
        source: "jobs",
        meta: "Melbourne \u00b7 posted 4d ago",
        summary: "Health analytics team, hybrid, no prior industry experience needed.",
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
  async updatePage(id, name, emoji) {
    await delay(100);
    const page = mockPages.find((p) => p.id === id)!;
    page.name = name;
    page.emoji = emoji;
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
  async createBlock(query, pageId, on) {
    const source = inferSource(query);
    // Mirrors the real agent's steps so mock mode demos the same experience,
    // just faster — no LLM behind it.
    const place: Record<string, string> = {
      gmail: "your inbox",
      papers: "research papers",
      youtube: "YouTube",
      news: "the news",
      sports: "scores and fixtures",
      jobs: "job listings",
      web: "the web",
      site: "that page",
    };
    const block = (status: Block["status"]): Block => ({
      id: crypto.randomUUID(),
      page_id: pageId,
      title: titleFrom(query),
      query,
      source,
      layout: defaultLayout(source),
      status,
      items: [fakeItem(query, source)],
      max_items: 3,
    });

    on?.created?.(block("loading"));
    on?.progress?.("Working out where to look…");
    await delay(700);
    on?.progress?.(`Searching ${place[source] ?? "the web"} for “${query}”`);
    await delay(700);
    on?.progress?.("Reviewing 3 results");
    on?.preview?.(block("loading")); // results, before the block is final
    await delay(900);
    return block("ready");
  },
  async rebuildBlock(id, on) {
    // Same shape as createBlock; the mock has no rows, so it just replays.
    const block = seed.find((b) => b.id === id);
    return this.createBlock(block?.query ?? "rebuilt block", block?.page_id ?? "default", on);
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
  async getBriefing() {
    await delay(150);
    return null;
  },
  async generateBriefing() {
    await delay(1500);
    return {
      id: crypto.randomUUID(),
      text: "Mock briefing — 3 new med-AI papers today, the Nature one on clinical LLMs is the standout. Your inbox has 2 newsletters worth opening; the rest is noise.",
      created_at: new Date().toISOString(),
    };
  },
};
