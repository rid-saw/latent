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
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-2xl border border-neutral-800 bg-neutral-900 p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-semibold">Create a block</h2>
          <button onClick={onClose} className="text-neutral-500 hover:text-neutral-200">
            <X size={18} />
          </button>
        </div>

        <p className="mb-2 text-sm text-neutral-400">
          Describe what you want to keep up with. The agent finds and ranks the
          content for this block.
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
          className="w-full resize-none rounded-lg border border-neutral-700 bg-neutral-950 p-3 text-sm outline-none focus:border-neutral-500"
        />

        <div className="mt-3 flex flex-wrap gap-2">
          {examples.map((ex) => (
            <button
              key={ex}
              onClick={() => setQuery(ex)}
              className="rounded-full border border-neutral-800 px-3 py-1 text-xs text-neutral-400 hover:border-neutral-600 hover:text-neutral-200"
            >
              {ex}
            </button>
          ))}
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-lg px-3 py-2 text-sm text-neutral-400 hover:text-neutral-200"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={!query.trim() || creating}
            className="flex items-center gap-2 rounded-lg bg-neutral-100 px-4 py-2 text-sm font-medium text-neutral-900 hover:bg-white disabled:opacity-50"
          >
            {creating && <Loader2 size={14} className="animate-spin" />}
            Create block
          </button>
        </div>
      </div>
    </div>
  );
}
