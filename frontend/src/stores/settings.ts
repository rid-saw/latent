import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Theme = "light" | "dark";

interface SettingsState {
  theme: Theme;
  rundownEnabled: boolean; // auto-generate the briefing on load
  sidebarOpen: boolean; // expanded sidebar vs collapsed icon rail
  autoRefreshMins: number; // 0 = off
  setTheme: (theme: Theme) => void;
  setRundownEnabled: (enabled: boolean) => void;
  setSidebarOpen: (open: boolean) => void;
  setAutoRefreshMins: (mins: number) => void;
}

export const useSettings = create<SettingsState>()(
  persist(
    (set) => ({
      theme: "light",
      rundownEnabled: true,
      sidebarOpen: true,
      autoRefreshMins: 30,
      setTheme: (theme) => set({ theme }),
      setRundownEnabled: (rundownEnabled) => set({ rundownEnabled }),
      setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
      setAutoRefreshMins: (autoRefreshMins) => set({ autoRefreshMins }),
    }),
    {
      name: "latent-settings",
      version: 3, // v3: rundown is a fixed strip again, no stored layout
      migrate: (state) => state as SettingsState,
    },
  ),
);
