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
      rundownLayout: { x: 0, y: 0, w: 5, h: 2 },
      sidebarOpen: true,
      setTheme: (theme) => set({ theme }),
      setRundownEnabled: (rundownEnabled) => set({ rundownEnabled }),
      setRundownLayout: (rundownLayout) => set({ rundownLayout }),
      setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
    }),
    { name: "latent-settings" },
  ),
);
