import { create } from "zustand";
import type { Block, BlockLayout } from "@/types";
import { api } from "@/api/client";
import { compactUp, findSpot } from "@/lib/layout";
import { diffAndRecord, forgetBlock } from "@/lib/seen";
import { usePages } from "./pages";

function occupiedLayouts(blocks: Block[]): BlockLayout[] {
  return blocks.filter((b) => b.layout.y < 1000).map((b) => b.layout);
}

const activePageId = () => usePages.getState().activePageId;

interface BlocksState {
  blocks: Block[];
  loading: boolean;
  loadedPageId: string | null; // which page the current blocks belong to
  creating: boolean;
  freshIds: Record<string, string[]>; // per block: item ids unseen before now
  load: () => Promise<void>;
  create: (query: string) => Promise<void>;
  remove: (id: string) => Promise<void>;
  refresh: (id: string) => Promise<void>;
  refreshAll: () => Promise<void>;
  applyLayouts: (layouts: Record<string, BlockLayout>) => void;
}

export const useBlocks = create<BlocksState>((set, get) => ({
  blocks: [],
  loading: false,
  loadedPageId: null,
  creating: false,
  freshIds: {},

  async load() {
    const pageId = activePageId();
    set({ loading: true });
    const blocks = await api.listBlocks(pageId);
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
    set({ creating: true });
    const block = await api.createBlock(query, activePageId());
    // Reading order: first free spot left->right, wrapping to the next row.
    const spot = findSpot(block.layout.w, block.layout.h, occupiedLayouts(get().blocks));
    const placed = { ...block, layout: { ...block.layout, ...spot } };
    set((s) => ({ blocks: [...s.blocks, placed], creating: false }));
    persistLayouts({ [placed.id]: placed.layout });
  },

  async remove(id) {
    await api.deleteBlock(id);
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
    const updated = await api.refreshBlock(block);
    const fresh = diffAndRecord(id, updated.items.map((i) => i.id));
    set((s) => ({
      blocks: s.blocks.map((b) => (b.id === id ? updated : b)),
      freshIds: { ...s.freshIds, [id]: fresh },
    }));
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
    api.saveLayouts(batch).catch(() => {});
  }, 800);
}
