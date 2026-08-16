import { useEffect, useState } from "react";
import { AlertCircle, Check, Loader2 } from "lucide-react";
import type { PendingBlock } from "@/stores/blocks";
import { useBlocks } from "@/stores/blocks";
import { BlockCard } from "./BlockCard";

/** A block being built, shown on the grid so the dashboard stays usable.
 *
 * Three states: the agent's steps while it works, the results once they
 * exist but before the block is saved, and the error if it failed. */
export function PendingCard({ pending }: { pending: PendingBlock }) {
  const { dismissPending, retryPending } = useBlocks();

  if (pending.error) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 rounded-xl border border-red-500/30 bg-card p-4 text-center">
        <AlertCircle size={18} className="text-red-500" />
        <p className="text-xs font-medium">Couldn't build this block</p>
        <p className="line-clamp-2 text-xs text-faint">"{pending.query}"</p>
        <p className="line-clamp-3 text-xs leading-relaxed text-soft">{pending.error}</p>
        <div className="mt-1 flex gap-2">
          {/* "Delete" rather than "Dismiss": nothing was saved here, so the
              two differ technically, but the user can't see that distinction
              and one word for one apparent action beats being precise. */}
          <button
            onClick={() => dismissPending(pending.id)}
            className="rounded-lg px-3 py-1.5 text-xs text-soft hover:text-ink"
          >
            Delete
          </button>
          <button
            onClick={() => retryPending(pending.id)}
            className="rounded-lg border border-line px-3 py-1.5 text-xs text-soft hover:text-ink"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  // Results are in but the block isn't saved yet. Shown straight away, with
  // a quiet note that it isn't settled.
  if (pending.preview) {
    return (
      <div className="relative h-full">
        <BlockCard block={pending.preview} readOnly />
        <span className="pointer-events-none absolute bottom-2 right-2 z-10 flex items-center gap-1.5 rounded-full bg-card/90 px-2 py-1 text-[10px] text-faint shadow backdrop-blur-sm">
          <Loader2 size={10} className="animate-spin" /> finishing up
        </span>
      </div>
    );
  }

  return <Steps pending={pending} />;
}

function Steps({ pending }: { pending: PendingBlock }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const started = Date.now();
    const timer = setInterval(
      () => setElapsed(Math.floor((Date.now() - started) / 1000)),
      1000,
    );
    return () => clearInterval(timer);
  }, [pending.id]);

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-dashed border-line bg-card/60 p-3">
      <div className="mb-2 flex items-start gap-2">
        <p className="line-clamp-2 flex-1 text-sm font-medium text-soft">{pending.query}</p>
        <span className="shrink-0 tabular-nums text-[10px] text-faint">{elapsed}s</span>
      </div>

      <ol className="min-h-0 flex-1 space-y-1.5 overflow-auto">
        {pending.steps.length === 0 && (
          <li className="flex items-center gap-2 text-xs text-faint">
            <Loader2 size={12} className="animate-spin" /> Starting…
          </li>
        )}
        {pending.steps.map((step, i) => {
          const current = i === pending.steps.length - 1;
          return (
            <li key={`${i}-${step}`} className="flex items-start gap-2 text-xs">
              {current ? (
                <Loader2 size={12} className="mt-px shrink-0 animate-spin text-accent" />
              ) : (
                <Check size={12} className="mt-px shrink-0 text-emerald-600" />
              )}
              <span className={current ? "text-soft" : "text-faint"}>{step}</span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
