import { useState } from "react";
import { X } from "lucide-react";
import { useBlocks } from "@/stores/blocks";

// One per source, and the first three need no Google account, so a first-time
// click lands somewhere that works. The headphones one is deliberate: it's the
// case a news feed could never answer, and shows this isn't a news reader.
const examples = [
  "Recent papers on Agentic AI",
  "Best noise-cancelling headphones under $300",
  "Most recent videos from Fireship",
  "NBA headlines from last night",
];

export function CreateBlockModal({ onClose }: { onClose: () => void }) {
  const create = useBlocks((s) => s.create);
  const [query, setQuery] = useState("");

  /** Building a block takes the better part of a minute. Rather than hold the
   *  screen for it, hand the work to a card on the grid and get out of the
   *  way: progress, results and any error all land there. */
  function submit() {
    if (!query.trim()) return;
    void create(query.trim());
    onClose();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-2xl border border-line bg-card p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-semibold">Create a block</h2>
          <button onClick={onClose} className="text-faint hover:text-ink">
            <X size={18} />
          </button>
        </div>

        <p className="mb-2 text-sm text-soft">
          Describe what you want to keep up with, or paste a URL to pin that
          site. The agent finds and ranks the content for this block.
        </p>

        <textarea
          autoFocus
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === "Enter") submit();
          }}
          rows={3}
          placeholder="e.g. Recent high-traffic papers on AI in medicine"
          className="w-full resize-none rounded-lg border border-line bg-bg p-3 text-sm outline-none focus:border-accent"
        />

        <div className="mt-3 flex flex-wrap gap-2">
          {examples.map((ex) => (
            <button
              key={ex}
              onClick={() => setQuery(ex)}
              className="rounded-full border border-line px-3 py-1 text-xs text-soft hover:border-faint hover:text-ink"
            >
              {ex}
            </button>
          ))}
        </div>

        {/* The hint gives up width first; the buttons never shrink, so their
            labels can't wrap. */}
        <div className="mt-5 flex items-center justify-between gap-3">
          <p className="min-w-0 text-xs text-faint">
            Takes up to a minute. You can keep working while it builds.
          </p>
          <div className="flex shrink-0 gap-2">
            <button
              onClick={onClose}
              className="whitespace-nowrap rounded-lg px-3 py-2 text-sm text-soft hover:text-ink"
            >
              Cancel
            </button>
            <button
              onClick={submit}
              disabled={!query.trim()}
              className="whitespace-nowrap rounded-lg bg-ink px-4 py-2 text-sm font-medium text-bg hover:opacity-90 disabled:opacity-50"
            >
              Create block
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
