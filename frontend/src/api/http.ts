import type { Api } from "./client";
import type { Block, BlockLayout, Page, Briefing } from "@/types";
import { ApiError, readDetail } from "@/lib/errors";

const base = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// Creating a block runs two CLI calls (~47s), and the backend gives up at 180s.
// A ceiling above that means a wedged request always ends in an error we can
// show, never in a spinner that runs forever.
const TIMEOUT_MS = 240_000;

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${base}${path}`, {
      headers: { "Content-Type": "application/json" },
      signal: AbortSignal.timeout(TIMEOUT_MS),
      ...init,
    });
  } catch (e) {
    // fetch only rejects when the request never completed: backend down, CORS,
    // offline, or our own timeout firing.
    const timedOut = e instanceof DOMException && e.name === "TimeoutError";
    throw new ApiError(
      timedOut ? "The request timed out" : "Could not reach the backend",
      timedOut ? 408 : 0,
    );
  }
  if (!res.ok) throw new ApiError(await readDetail(res), res.status);
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
