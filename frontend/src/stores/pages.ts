import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Page } from "@/types";
import { api } from "@/api/client";

interface PagesState {
  pages: Page[];
  activePageId: string;
  load: () => Promise<void>;
  add: (name: string, emoji: string) => Promise<void>;
  update: (id: string, name: string, emoji: string) => Promise<void>;
  remove: (id: string) => Promise<void>;
  setActive: (id: string) => void;
}

export const usePages = create<PagesState>()(
  persist(
    (set, get) => ({
      pages: [],
      activePageId: "default",

      async load() {
        const pages = await api.listPages();
        const active = pages.some((p) => p.id === get().activePageId)
          ? get().activePageId
          : (pages[0]?.id ?? "default");
        set({ pages, activePageId: active });
      },

      async add(name, emoji) {
        const page = await api.createPage(name, emoji);
        set((s) => ({ pages: [...s.pages, page], activePageId: page.id }));
      },

      async update(id, name, emoji) {
        const page = await api.updatePage(id, name, emoji);
        set((s) => ({ pages: s.pages.map((p) => (p.id === id ? page : p)) }));
      },

      async remove(id) {
        await api.deletePage(id);
        set((s) => {
          const pages = s.pages.filter((p) => p.id !== id);
          return {
            pages,
            activePageId:
              s.activePageId === id ? (pages[0]?.id ?? "default") : s.activePageId,
          };
        });
      },

      setActive(id) {
        set({ activePageId: id });
      },
    }),
    { name: "latent-pages", partialize: (s) => ({ activePageId: s.activePageId }) },
  ),
);
