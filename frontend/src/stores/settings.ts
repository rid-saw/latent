import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Theme = "light" | "dark";

interface SettingsState {
  theme: Theme;
  briefingEnabled: boolean; // auto-generate the briefing on load
  sidebarOpen: boolean; // expanded sidebar vs collapsed icon rail
  autoRefreshMins: number; // 0 = off
  setTheme: (theme: Theme) => void;
  setBriefingEnabled: (enabled: boolean) => void;
  setSidebarOpen: (open: boolean) => void;
  setAutoRefreshMins: (mins: number) => void;
}

export const useSettings = create<SettingsState>()(
  persist(
    (set) => ({
      theme: "light",
      briefingEnabled: true,
      sidebarOpen: true,
      autoRefreshMins: 30,
      setTheme: (theme) => set({ theme }),
      setBriefingEnabled: (briefingEnabled) => set({ briefingEnabled }),
      setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
      setAutoRefreshMins: (autoRefreshMins) => set({ autoRefreshMins }),
    }),
    {
      name: "latent-settings",
      version: 4, // v4: "rundown" renamed to "briefing"
      migrate: (state) => {
        const s = state as SettingsState & { rundownEnabled?: boolean };
        if (s && s.rundownEnabled !== undefined && s.briefingEnabled === undefined) {
          s.briefingEnabled = s.rundownEnabled;
          delete s.rundownEnabled;
        }
        return s;
      },
    },
  ),
);
