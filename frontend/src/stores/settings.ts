import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { BlockLayout } from "@/types";

export type Theme = "light" | "dark";

interface SettingsState {
  theme: Theme;
  rundownEnabled: boolean; // auto-generate the briefing on load
  rundownLayout: BlockLayout; // the rundown is a grid block; position persists here
  sidebarOpen: boolean; // expanded sidebar vs collapsed icon rail
  setTheme: (theme: Theme) => void;
  setRundownEnabled: (enabled: boolean) => void;
  setRundownLayout: (layout: BlockLayout) => void;
  setSidebarOpen: (open: boolean) => void;
}

export const useSettings = create<SettingsState>()(
  persist(
    (set) => ({
      theme: "light",
      rundownEnabled: true,
      rundownLayout: { x: 7, y: 0, w: 5, h: 2 }, // top-right corner (12-col grid)
      sidebarOpen: true,
      setTheme: (theme) => set({ theme }),
      setRundownEnabled: (rundownEnabled) => set({ rundownEnabled }),
      setRundownLayout: (rundownLayout) => set({ rundownLayout }),
      setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
    }),
    {
      name: "latent-settings",
      version: 2,
      migrate: (state, version) => {
        // v2: rundown moved to the top-right corner by default.
        if (version < 2 && state && typeof state === "object") {
          (state as SettingsState).rundownLayout = { x: 7, y: 0, w: 5, h: 2 };
        }
        return state as SettingsState;
      },
    },
  ),
);
