import { create } from "zustand";
import type { Block, BlockLayout } from "@/types";
import { api } from "@/api/client";
import { compactUp, findSpot } from "@/lib/layout";

function occupiedLayouts(blocks: Block[]): BlockLayout[] {
  return blocks.filter((b) => b.layout.y < 1000).map((b) => b.layout);
}

interface BlocksState {
  blocks: Block[];
  loading: boolean;
  creating: boolean;
  load: () => Promise<void>;
  create: (query: string) => Promise<void>;
  remove: (id: string) => Promise<void>;
  refresh: (id: string) => Promise<void>;
  applyLayouts: (layouts: Record<string, BlockLayout>) => void;
}

export const useBlocks = create<BlocksState>((set, get) => ({
  blocks: [],
  loading: false,
  creating: false,

  async load() {
    set({ loading: true });
    const blocks = await api.listBlocks();
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
    set({ blocks, loading: false });
    if (Object.keys(fixed).length) persistLayouts(fixed);
  },

  async create(query) {
    set({ creating: true });
    const block = await api.createBlock(query);
    // Reading order: first free spot left->right, wrapping to the next row.
    const spot = findSpot(block.layout.w, block.layout.h, occupiedLayouts(get().blocks));
    const placed = { ...block, layout: { ...block.layout, ...spot } };
    set((s) => ({ blocks: [...s.blocks, placed], creating: false }));
    persistLayouts({ [placed.id]: placed.layout });
  },

  async remove(id) {
    await api.deleteBlock(id);
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
    set((s) => ({ blocks: s.blocks.map((b) => (b.id === id ? updated : b)) }));
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
