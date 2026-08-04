import { create } from "zustand";
import type { Block, BlockLayout } from "@/types";
import { api } from "@/api/client";
import { friendlyError } from "@/lib/errors";
import { compactUp, findSpot } from "@/lib/layout";
import { diffAndRecord, forgetBlock } from "@/lib/seen";
import { toast } from "./toasts";
import { usePages } from "./pages";

function occupiedLayouts(blocks: Block[]): BlockLayout[] {
  return blocks.filter((b) => b.layout.y < 1000).map((b) => b.layout);
}

const activePageId = () => usePages.getState().activePageId;

interface BlocksState {
  blocks: Block[];
  loading: boolean;
  loadError: string | null; // page-level failure (backend down, etc.)
  loadedPageId: string | null; // which page the current blocks belong to
  creating: boolean;
  progress: string[]; // the agent's steps for the block being created
  freshIds: Record<string, string[]>; // per block: item ids unseen before now
  load: () => Promise<void>;
  /** Resolves to an error message the caller should show, or null on success. */
  create: (query: string) => Promise<string | null>;
  remove: (id: string) => Promise<void>;
  refresh: (id: string) => Promise<void>;
  refreshAll: () => Promise<void>;
  applyLayouts: (layouts: Record<string, BlockLayout>) => void;
}

// Every action below owns its failures. Nothing here is allowed to throw: an
// unhandled rejection leaves `loading`/`creating` stuck on and the UI dead.
export const useBlocks = create<BlocksState>((set, get) => ({
  blocks: [],
  loading: false,
  loadError: null,
  loadedPageId: null,
  creating: false,
  progress: [],
  freshIds: {},

  async load() {
    const pageId = activePageId();
    set({ loading: true, loadError: null });
    let blocks: Block[];
    try {
      blocks = await api.listBlocks(pageId);
    } catch (e) {
      // Keep whatever is on screen; show the reason instead of an endless skeleton.
      set({ loading: false, loadError: friendlyError(e), loadedPageId: pageId });
      return;
    }
    // Free-form grid (no compaction): normalize legacy "place at bottom"
    // sentinels (y >= 1000) into real reading-order positions.
    const occupied = occupiedLayouts(blocks);
    const fixed: Record<string, Block["layout"]> = {};
    for (const b of blocks) {
      if (b.layout.y >= 1000) {
        b.layout = { ...b.layout, ...findSpot(b.layout.w, b.layout.h, occupied) };
        occupied.push(b.layout);
        fixed[b.id] = b.layout;
      }
    }
    const freshIds: Record<string, string[]> = {};
    for (const b of blocks) {
      freshIds[b.id] = diffAndRecord(b.id, b.items.map((i) => i.id));
    }
    set({ blocks, loading: false, loadedPageId: pageId, freshIds });
    if (Object.keys(fixed).length) persistLayouts(fixed);
  },

  async create(query) {
    set({ creating: true, progress: [] });
    let block: Block;
    try {
      block = await api.createBlock(query, activePageId(), (message) =>
        set((s) => ({ progress: [...s.progress, message] })),
      );
    } catch (e) {
      // The modal stays open and shows this, so the typed query isn't lost.
      return friendlyError(e);
    } finally {
      // Progress survives a failure so the modal can show how far it got.
      set({ creating: false });
    }
    // Reading order: first free spot left->right, wrapping to the next row.
    const spot = findSpot(block.layout.w, block.layout.h, occupiedLayouts(get().blocks));
    const placed = { ...block, layout: { ...block.layout, ...spot } };
    set((s) => ({ blocks: [...s.blocks, placed] }));
    persistLayouts({ [placed.id]: placed.layout });
    return null;
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
    const { blocks, changed } = compactUp(get().blocks.filter((b) => b.id !== id));
    set({ blocks });
    if (Object.keys(changed).length) persistLayouts(changed);
  },

  async refresh(id) {
    const block = get().blocks.find((b) => b.id === id);
    if (!block) return;
    set((s) => ({
      blocks: s.blocks.map((b) => (b.id === id ? { ...b, status: "loading" } : b)),
    }));
    try {
      const updated = await api.refreshBlock(block);
      const fresh = diffAndRecord(id, updated.items.map((i) => i.id));
      set((s) => ({
        blocks: s.blocks.map((b) => (b.id === id ? updated : b)),
        freshIds: { ...s.freshIds, [id]: fresh },
      }));
    } catch (e) {
      // The card renders its own error state with a retry button.
      set((s) => ({
        blocks: s.blocks.map((b) => (b.id === id ? { ...b, status: "error" } : b)),
      }));
      toast(friendlyError(e));
    }
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
    }));
    persistLayouts(layouts);
  },
}));

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
