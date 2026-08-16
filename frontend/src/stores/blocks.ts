import { create } from "zustand";
import type { Block, BlockLayout } from "@/types";
import { api } from "@/api/client";
import { ApiError, OFFLINE, friendlyError, isOffline } from "@/lib/errors";
import { compactUp, findSpot } from "@/lib/layout";
import { diffAndRecord, forgetBlock } from "@/lib/seen";
import { toast } from "./toasts";
import { usePages } from "./pages";

function occupiedLayouts(blocks: Block[]): BlockLayout[] {
  return blocks.filter((b) => b.layout.y < 1000).map((b) => b.layout);
}

const activePageId = () => usePages.getState().activePageId;

/** A block being built. Lives on the grid so the dashboard stays usable while
 *  the agent works, and so a failure has somewhere to be reported. */
export interface PendingBlock {
  id: string; // local only, for React keys
  created: Block | null; // the row the backend wrote; null until it says so
  pageId: string; // which page it belongs to, so it doesn't follow you around
  query: string;
  steps: string[]; // agent progress, newest last
  preview: Block | null; // results, shown as soon as the fetch returns
  error: string | null;
  layout: BlockLayout;
  resized: boolean; // user set the size; don't overwrite it with the default
}

interface BlocksState {
  blocks: Block[];
  pending: PendingBlock[];
  loading: boolean;
  loadError: string | null; // page-level failure (backend down, etc.)
  loadedPageId: string | null; // which page the current blocks belong to
  freshIds: Record<string, string[]>; // per block: item ids unseen before now
  load: () => Promise<void>;
  create: (query: string) => Promise<void>;
  dismissPending: (id: string) => void;
  retryPending: (id: string) => Promise<void>;
  remove: (id: string) => Promise<void>;
  refresh: (id: string) => Promise<void>;
  /** Try again on a failed block. Picks refetch or re-route for you. */
  retry: (id: string) => Promise<void>;
  refreshAll: () => Promise<void>;
  applyLayouts: (layouts: Record<string, BlockLayout>) => void;
}

// Every action below owns its failures. Nothing here is allowed to throw: an
// unhandled rejection leaves a spinner stuck on with nobody to clear it.
export const useBlocks = create<BlocksState>((set, get) => ({
  blocks: [],
  pending: [],
  loading: false,
  loadError: null,
  loadedPageId: null,
  freshIds: {},

  async load() {
    const pageId = activePageId();
    set({ loading: true, loadError: null });
    let blocks: Block[];
    try {
      blocks = await api.listBlocks(pageId);
    } catch (e) {
      // Keep whatever is on screen; show the reason instead of an endless skeleton.
      set({
        loading: false,
        loadError: friendlyError(e),
        loadedPageId: pageId,
      });
      return;
    }
    // Free-form grid (no compaction): normalize legacy "place at bottom"
    // sentinels (y >= 1000) into real reading-order positions.
    const occupied = occupiedLayouts(blocks);
    const fixed: Record<string, Block["layout"]> = {};
    for (const b of blocks) {
      if (b.layout.y >= 1000) {
        b.layout = {
          ...b.layout,
          ...findSpot(b.layout.w, b.layout.h, occupied),
        };
        occupied.push(b.layout);
        fixed[b.id] = b.layout;
      }
    }
    // A row left at "loading" was interrupted: the browser driving it is
    // gone, so nothing will ever finish it. Shown as failed, which is true
    // and puts a Try again in front of the user.
    for (const b of blocks) {
      if (b.status === "loading") b.status = "error";
    }
    const freshIds: Record<string, string[]> = {};
    for (const b of blocks) {
      freshIds[b.id] = diffAndRecord(
        b.id,
        b.items.map((i) => i.id),
      );
    }
    set({ blocks, loading: false, loadedPageId: pageId, freshIds });
    if (Object.keys(fixed).length) persistLayouts(fixed);
  },

  async create(query) {
    // Reading order: first free spot left->right, wrapping to the next row.
    // Claimed up front so the finished block lands where the card already is.
    const occupied = [
      ...occupiedLayouts(get().blocks),
      ...get().pending.map((p) => p.layout),
    ];
    const layout = {
      ...PENDING_SIZE,
      ...findSpot(PENDING_SIZE.w, PENDING_SIZE.h, occupied),
    };
    const id = `${PENDING_PREFIX}${crypto.randomUUID()}`;
    set((s) => ({
      pending: [
        ...s.pending,
        {
          id,
          created: null,
          pageId: activePageId(),
          query,
          steps: [],
          preview: null,
          error: null,
          layout,
          resized: false,
        },
      ],
    }));
    await runCreate(set, get, id, (on) =>
      api.createBlock(query, activePageId(), on),
    );
  },

  dismissPending(id) {
    set((s) => ({ pending: s.pending.filter((p) => p.id !== id) }));
  },

  async retryPending(id) {
    // Only reachable when the backend was never contacted, so there is no row
    // to rebuild — this starts a fresh creation from the same prompt.
    const card = get().pending.find((p) => p.id === id);
    if (!card) return;
    patchPending(set, id, { steps: [], preview: null, error: null });
    await runCreate(set, get, id, (on) =>
      api.createBlock(card.query, activePageId(), on),
    );
  },

  async remove(id) {
    try {
      await api.deleteBlock(id);
    } catch (e) {
      // Leave the block on screen — pretending it's gone would be a lie.
      toast(friendlyError(e));
      return;
    }
    forgetBlock(id);
    // Gravity pass: neighbors slide up into the vacated space.
    const { blocks, changed } = compactUp(
      get().blocks.filter((b) => b.id !== id),
    );
    set({ blocks });
    if (Object.keys(changed).length) persistLayouts(changed);
  },

  async refresh(id) {
    const block = get().blocks.find((b) => b.id === id);
    if (!block) return;
    if (isOffline()) {
      // Say so and stop. Leaves the block as it was: a network problem is not
      // a reason to mark a healthy block failed.
      toast(OFFLINE);
      return;
    }
    set((s) => ({
      blocks: s.blocks.map((b) =>
        b.id === id ? { ...b, status: "loading" } : b,
      ),
    }));
    try {
      const updated = await api.refreshBlock(block);
      const fresh = diffAndRecord(
        id,
        updated.items.map((i) => i.id),
      );
      set((s) => ({
        blocks: s.blocks.map((b) => (b.id === id ? updated : b)),
        freshIds: { ...s.freshIds, [id]: fresh },
      }));
    } catch (e) {
      // The card renders its own error state with a retry button.
      set((s) => ({
        blocks: s.blocks.map((b) =>
          b.id === id ? { ...b, status: "error" } : b,
        ),
      }));
      toast(friendlyError(e));
    }
  },

  async retry(id) {
    const block = get().blocks.find((b) => b.id === id);
    if (!block) return;
    // No plan means routing never finished, so there is nothing to refetch —
    // it has to be built from the query again. That is the same work as
    // creating it, so it goes back through the same narrated path and
    // reappears as a card showing the agent's steps.
    if (block.plan?.search_terms) return get().refresh(id);

    if (isOffline()) {
      toast(OFFLINE);
      return;
    }
    const pendingId = `${PENDING_PREFIX}${crypto.randomUUID()}`;
    set((s) => ({
      blocks: s.blocks.filter((b) => b.id !== id),
      pending: [
        ...s.pending,
        {
          id: pendingId,
          created: block,
          pageId: block.page_id,
          query: block.query,
          steps: [],
          preview: null,
          error: null,
          layout: block.layout,
          resized: true, // the user already sized this one; leave it alone
        },
      ],
    }));
    await runCreate(set, get, pendingId, (on) => api.rebuildBlock(id, on));
  },

  async refreshAll() {
    // Quiet background refresh — free content APIs only, no LLM.
    await Promise.allSettled(get().blocks.map((b) => get().refresh(b.id)));
  },

  applyLayouts(layouts) {
    set((s) => ({
      blocks: s.blocks.map((b) =>
        layouts[b.id] ? { ...b, layout: layouts[b.id] } : b,
      ),
      // Pending cards are draggable too, and their layout is what the finished
      // block inherits — so a drag that isn't recorded here gets undone the
      // moment the agent returns.
      pending: s.pending.map((p) => {
        const next = layouts[p.id];
        if (!next) return p;
        const resized =
          p.resized || next.w !== p.layout.w || next.h !== p.layout.h;
        return { ...p, layout: next, resized };
      }),
    }));
    // Pending ids have no row yet; sending them would be a no-op round trip.
    const saved = Object.fromEntries(
      Object.entries(layouts).filter(([id]) => !id.startsWith(PENDING_PREFIX)),
    );
    if (Object.keys(saved).length) persistLayouts(saved);
  },
}));

// A pending card starts before its source is known, so it can't use that
// source's preferred size. It adopts one the moment the preview arrives,
// unless the user has already picked their own.
const PENDING_SIZE = { w: 8, h: 8 };

const PENDING_PREFIX = "pending-";

type StreamHandlers = {
  created?: (block: Block) => void;
  progress?: (message: string) => void;
  preview?: (block: Block) => void;
};

type Set = (fn: (s: BlocksState) => Partial<BlocksState>) => void;
type Get = () => BlocksState;

const entry = (get: Get, id: string) => get().pending.find((p) => p.id === id);

function patchPending(set: Set, id: string, patch: Partial<PendingBlock>) {
  set((s) => ({
    pending: s.pending.map((p) => (p.id === id ? { ...p, ...patch } : p)),
  }));
}

/** Drive one agent run to completion, reporting into its pending card.
 *
 *  `call` is the only difference between creating a block and rebuilding a
 *  failed one: same narration, same swap at the end, same failure handling. */
async function runCreate(
  set: Set,
  get: Get,
  id: string,
  call: (on: StreamHandlers) => Promise<Block>,
) {
  if (isOffline()) {
    // The provider CLIs retry for about three minutes before giving up, and a
    // run makes more than one call. Not worth starting.
    patchPending(set, id, { error: OFFLINE });
    return;
  }

  let block: Block;
  try {
    block = await call({
      // The row is already in the database by the time this fires, so from
      // here on the prompt is safe whatever happens to the connection.
      created: (b) => patchPending(set, id, { created: b }),
      progress: (message) =>
        set((s) => ({
          pending: s.pending.map((p) =>
            p.id === id ? { ...p, steps: [...p.steps, message] } : p,
          ),
        })),
      preview: (b) =>
        set((s) => ({
          pending: s.pending.map((p) => {
            if (p.id !== id) return p;
            // Take the source's preferred size now, while the card is still
            // visibly in progress. Doing it at the end instead would resize
            // the block under a user who had already settled it.
            const layout = p.resized
              ? p.layout
              : { ...p.layout, w: b.layout.w, h: b.layout.h };
            return { ...p, preview: b, layout };
          }),
        })),
    });
  } catch (e) {
    // Deleted while it was being built. The rescue below assumes the row
    // still exists; here it deliberately doesn't, and putting the block back
    // would resurrect the thing the user just removed — as a duplicate the
    // database has no row for, which then 404s on every later action and
    // vanishes on reload.
    if (e instanceof ApiError && e.status === 410) {
      set((s) => ({ pending: s.pending.filter((p) => p.id !== id) }));
      return;
    }
    // Two ways to end up with a real row here: the backend reported the
    // failure and sent the block with it, or it wrote the row up front and
    // the connection died before it could tell us anything else. Either way
    // the block exists, so the card hands over to it — retrying from the card
    // would otherwise write a second row for the same prompt.
    const reported =
      e instanceof ApiError ? (e.data?.block as Block | undefined) : undefined;
    const rescued = reported ?? entry(get, id)?.created ?? undefined;
    if (rescued) {
      const at = entry(get, id)?.layout ?? rescued.layout;
      set((s) => ({
        blocks: [...s.blocks, { ...rescued, layout: at, status: "error" }],
        pending: s.pending.filter((p) => p.id !== id),
      }));
      return;
    }
    patchPending(set, id, { error: friendlyError(e) });
    return;
  }

  // Inherit the card's layout exactly as it now stands, including any drag or
  // resize done while waiting, so nothing moves at the moment of the swap.
  const layout = entry(get, id)?.layout ?? block.layout;
  const placed = { ...block, layout };
  set((s) => ({
    blocks: [...s.blocks, placed],
    pending: s.pending.filter((p) => p.id !== id),
  }));
  persistLayouts({ [placed.id]: placed.layout });
}

// Debounced persistence — drag emits layout changes continuously.
let layoutTimer: ReturnType<typeof setTimeout> | undefined;
let pendingLayouts: Record<string, BlockLayout> = {};

function persistLayouts(layouts: Record<string, BlockLayout>) {
  pendingLayouts = { ...pendingLayouts, ...layouts };
  clearTimeout(layoutTimer);
  layoutTimer = setTimeout(() => {
    const batch = pendingLayouts;
    pendingLayouts = {};
    // Silent on failure by design: the layout is cosmetic and re-saves on the
    // next drag. A toast here would fire on every nudge while offline.
    api.saveLayouts(batch).catch(() => {});
  }, 800);
}
