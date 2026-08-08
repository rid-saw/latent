import type { Api } from "./client";
import type { Block, BlockLayout, Page, Briefing } from "@/types";
import { ApiError, readDetail } from "@/lib/errors";
import { revalidateGoogle } from "@/stores/auth";

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
  if (!res.ok) {
    // A 401 means the Google connection just died under us — re-check it so
    // the sidebar stops claiming "connected" while blocks are failing.
    if (res.status === 401) revalidateGoogle();
    throw new ApiError(await readDetail(res), res.status);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

/** Parses one SSE frame: "event: name\ndata: {...}". */
function parseFrame(frame: string): { event: string; data: Record<string, unknown> } | null {
  const event = /^event: (.+)$/m.exec(frame)?.[1];
  const raw = /^data: (.*)$/m.exec(frame)?.[1];
  if (!event || raw === undefined) return null;
  try {
    return { event, data: JSON.parse(raw) };
  } catch {
    return null; // a truncated frame is better skipped than thrown on
  }
}

/** Creates a block over SSE, reporting each agent step as it happens.
 *
 * The response is 200 the moment the stream opens, so failures arrive as an
 * "error" event rather than an HTTP status — they're re-thrown as ApiError so
 * every caller handles them identically to a normal request.
 */
async function streamBlock(
  path: string,
  body: unknown,
  on?: {
    created?: (block: Block) => void;
    progress?: (message: string) => void;
    preview?: (block: Block) => void;
  },
): Promise<Block> {
  let res: Response;
  try {
    res = await fetch(`${base}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
  } catch (e) {
    const timedOut = e instanceof DOMException && e.name === "TimeoutError";
    throw new ApiError(
      timedOut ? "The request timed out" : "Could not reach the backend",
      timedOut ? 408 : 0,
    );
  }
  if (!res.ok) {
    if (res.status === 401) revalidateGoogle();
    throw new ApiError(await readDetail(res), res.status);
  }
  if (!res.body) throw new ApiError("The backend sent no response stream", 0);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let block: Block | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? ""; // trailing partial frame waits for more bytes
    for (const frame of frames) {
      const parsed = parseFrame(frame);
      if (!parsed) continue;
      if (parsed.event === "created") {
        on?.created?.(parsed.data as unknown as Block);
      } else if (parsed.event === "progress") {
        on?.progress?.(String(parsed.data.message ?? ""));
      } else if (parsed.event === "preview") {
        on?.preview?.(parsed.data as unknown as Block);
      } else if (parsed.event === "block") {
        block = parsed.data as unknown as Block;
      } else if (parsed.event === "error") {
        const status = Number(parsed.data.status) || 500;
        if (status === 401) revalidateGoogle();
        // parsed.data carries the block the backend saved, so the caller can
        // put it on the grid instead of losing the query with the error.
        throw new ApiError(
          String(parsed.data.detail ?? "Block creation failed"),
          status,
          parsed.data,
        );
      }
    }
  }
  if (!block) throw new ApiError("The backend closed without creating a block", 0);
  return block;
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
  createBlock: (query, pageId, on) =>
    streamBlock("/api/blocks/stream", { query, page_id: pageId }, on),
  rebuildBlock: (id, on) => streamBlock(`/api/blocks/${id}/rebuild`, {}, on),
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
