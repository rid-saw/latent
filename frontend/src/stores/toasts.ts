import { create } from "zustand";

export interface Toast {
  id: string;
  message: string;
  tone: "error" | "info";
}

interface ToastState {
  toasts: Toast[];
  push: (message: string, tone?: Toast["tone"]) => void;
  dismiss: (id: string) => void;
}

const LIFETIME_MS = 7000;

export const useToasts = create<ToastState>((set, get) => ({
  toasts: [],

  push(message, tone = "error") {
    // Don't stack duplicates: a failing auto-refresh hits every block at once.
    if (get().toasts.some((t) => t.message === message)) return;
    const id = crypto.randomUUID();
    set((s) => ({ toasts: [...s.toasts, { id, message, tone }] }));
    setTimeout(() => get().dismiss(id), LIFETIME_MS);
  },

  dismiss(id) {
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
  },
}));

/** Fire-and-forget helper for stores: `toast("Couldn't refresh that block")`. */
export const toast = (message: string, tone?: Toast["tone"]) =>
  useToasts.getState().push(message, tone);
