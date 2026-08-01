import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Page } from "@/types";
import { api } from "@/api/client";
import { friendlyError } from "@/lib/errors";
import { toast } from "./toasts";

interface PagesState {
  pages: Page[];
  activePageId: string;
  load: () => Promise<void>;
  add: (name: string, emoji: string) => Promise<void>;
  update: (id: string, name: string, emoji: string) => Promise<void>;
  remove: (id: string) => Promise<void>;
  setActive: (id: string) => void;
}

// As in the blocks store: these never throw. The sidebar is the first thing
// that renders, so a failure here must not take the whole app down with it.
export const usePages = create<PagesState>()(
  persist(
    (set, get) => ({
      pages: [],
      activePageId: "default",

      async load() {
        let pages: Page[];
        try {
          pages = await api.listPages();
        } catch (e) {
          toast(friendlyError(e));
          return;
        }
        const active = pages.some((p) => p.id === get().activePageId)
          ? get().activePageId
          : (pages[0]?.id ?? "default");
        set({ pages, activePageId: active });
      },

      async add(name, emoji) {
        try {
          const page = await api.createPage(name, emoji);
          set((s) => ({ pages: [...s.pages, page], activePageId: page.id }));
        } catch (e) {
          toast(friendlyError(e));
        }
      },

      async update(id, name, emoji) {
        try {
          const page = await api.updatePage(id, name, emoji);
          set((s) => ({ pages: s.pages.map((p) => (p.id === id ? page : p)) }));
        } catch (e) {
          toast(friendlyError(e));
        }
      },

      async remove(id) {
        try {
          await api.deletePage(id);
        } catch (e) {
          toast(friendlyError(e));
          return;
        }
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
