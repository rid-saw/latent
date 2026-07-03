import { create } from "zustand";
import type { Block, BlockLayout } from "@/types";
import { api } from "@/api/client";

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
    set({ blocks, loading: false });
  },

  async create(query) {
    set({ creating: true });
    const block = await api.createBlock(query);
    set((s) => ({ blocks: [...s.blocks, block], creating: false }));
  },

  async remove(id) {
    await api.deleteBlock(id);
    set((s) => ({ blocks: s.blocks.filter((b) => b.id !== id) }));
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
