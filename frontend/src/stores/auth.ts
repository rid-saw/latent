import { create } from "zustand";

const base = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const mock = import.meta.env.VITE_USE_MOCK !== "false";

export type GoogleStatus = "checking" | "connected" | "expired" | "not_connected";

interface AuthState {
  google: GoogleStatus;
  check: () => Promise<void>;
}

/** Live Google connection status.
 *
 * Checked once on load, and re-checked whenever a request comes back 401 —
 * a token can die mid-session, and a card that never rechecks would keep
 * claiming "connected" while every block quietly fails.
 */
export const useAuth = create<AuthState>((set) => ({
  google: "checking",

  async check() {
    if (mock) return;
    try {
      const res = await fetch(`${base}/api/auth/status`);
      const s = await res.json();
      set({ google: s.google ? "connected" : (s.reason ?? "not_connected") });
    } catch {
      set({ google: "not_connected" });
    }
  },
}));

let inFlight: Promise<void> | null = null;

/** Called from the API error path on a 401. Collapses concurrent calls into
 *  one request — refreshAll() can 401 on every block at the same moment. */
export function revalidateGoogle() {
  if (inFlight) return;
  inFlight = useAuth
    .getState()
    .check()
    .finally(() => {
      inFlight = null;
    });
}
