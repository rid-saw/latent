import { useState } from "react";
import { Loader2, X } from "lucide-react";
import { useBlocks } from "@/stores/blocks";

const examples = [
  "Recent papers on AI and medicine",
  "New videos from AI research channels",
  "NBA headlines from last night",
  "Newsletters about startups in my inbox",
];

export function CreateBlockModal({ onClose }: { onClose: () => void }) {
  const { create, creating } = useBlocks();
  const [query, setQuery] = useState("");

  async function submit() {
    if (!query.trim()) return;
    await create(query.trim());
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

        <div className="mt-5 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-lg px-3 py-2 text-sm text-soft hover:text-ink"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={!query.trim() || creating}
            className="flex items-center gap-2 rounded-lg bg-ink px-4 py-2 text-sm font-medium text-bg hover:opacity-90 disabled:opacity-50"
          >
            {creating && <Loader2 size={14} className="animate-spin" />}
            Create block
          </button>
        </div>
      </div>
    </div>
  );
}
