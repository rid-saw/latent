import { AlertCircle, Info, X } from "lucide-react";
import { useToasts } from "@/stores/toasts";

/** Bottom-right stack of transient messages. Mounted once, in App. */
export function Toaster() {
  const { toasts, dismiss } = useToasts();
  if (!toasts.length) return null;

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[70] flex w-full max-w-sm flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          role="status"
          className="pointer-events-auto flex items-start gap-2.5 rounded-xl border border-line bg-card p-3 shadow-lg"
        >
          {t.tone === "error" ? (
            <AlertCircle size={16} className="mt-0.5 shrink-0 text-red-500" />
          ) : (
            <Info size={16} className="mt-0.5 shrink-0 text-accent" />
          )}
          <p className="flex-1 text-sm leading-snug text-soft">{t.message}</p>
          <button
            onClick={() => dismiss(t.id)}
            className="shrink-0 text-faint hover:text-ink"
            title="Dismiss"
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}
