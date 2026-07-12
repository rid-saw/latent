import type { Api } from "./client";
import type { Block, BlockLayout, Page, Briefing } from "@/types";

const base = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.status === 204 ? (undefined as T) : res.json();
}

export const httpApi: Api = {
  listPages: () => req<Page[]>("/api/pages"),
  createPage: (name, emoji) =>
    req<Page>("/api/pages", { method: "POST", body: JSON.stringify({ name, emoji }) }),
  updatePage: (id, name, emoji) =>
    req<Page>(`/api/pages/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ name, emoji }),
    }),
  deletePage: (id) => req<void>(`/api/pages/${id}`, { method: "DELETE" }),
  listBlocks: (pageId) => req<Block[]>(`/api/blocks?page_id=${pageId}`),
  createBlock: (query, pageId) =>
    req<Block>("/api/blocks", {
      method: "POST",
      body: JSON.stringify({ query, page_id: pageId }),
    }),
  refreshBlock: (block) =>
    req<Block>(`/api/blocks/${block.id}/refresh`, { method: "POST" }),
  deleteBlock: (id) => req<void>(`/api/blocks/${id}`, { method: "DELETE" }),
  saveLayouts: (layouts: Record<string, BlockLayout>) =>
    req<void>("/api/blocks/layouts", {
      method: "PATCH",
      body: JSON.stringify(layouts),
    }),
  getBriefing: (pageId) => req<Briefing | null>(`/api/briefing?page_id=${pageId}`),
  generateBriefing: (pageId) =>
    req<Briefing>(`/api/briefing?page_id=${pageId}`, { method: "POST" }),
};
