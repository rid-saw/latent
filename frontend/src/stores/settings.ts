import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Theme = "light" | "dark";

interface SettingsState {
  theme: Theme;
  rundownEnabled: boolean; // auto-generate the briefing on load
  sidebarOpen: boolean; // expanded sidebar vs collapsed icon rail
  setTheme: (theme: Theme) => void;
  setRundownEnabled: (enabled: boolean) => void;
  setSidebarOpen: (open: boolean) => void;
}

export const useSettings = create<SettingsState>()(
  persist(
    (set) => ({
      theme: "light",
      rundownEnabled: true,
      sidebarOpen: true,
      setTheme: (theme) => set({ theme }),
      setRundownEnabled: (rundownEnabled) => set({ rundownEnabled }),
      setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
    }),
    { name: "latent-settings" },
  ),
);
