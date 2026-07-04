import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Theme = "light" | "dark";

interface SettingsState {
  theme: Theme;
  rundownEnabled: boolean; // auto-generate the briefing on load
  setTheme: (theme: Theme) => void;
  setRundownEnabled: (enabled: boolean) => void;
}

export const useSettings = create<SettingsState>()(
  persist(
    (set) => ({
      theme: "light",
      rundownEnabled: true,
      setTheme: (theme) => set({ theme }),
      setRundownEnabled: (rundownEnabled) => set({ rundownEnabled }),
    }),
    { name: "latent-settings" },
  ),
);
