import { useEffect, useState } from "react";
import { AlertCircle, Check, Loader2, X } from "lucide-react";
import { useBlocks } from "@/stores/blocks";

/** The agent's steps, streamed live. Creating a block runs two LLM calls and
 *  takes ~47s; the elapsed counter keeps something moving through the long
 *  silences while a single step is still thinking. */
function AgentProgress({ steps, running }: { steps: string[]; running: boolean }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!running) return;
    const started = Date.now();
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [running]);

  if (!steps.length) return null;

  return (
    <ol className="mt-3 space-y-1.5 rounded-lg border border-line bg-bg p-3">
      {steps.map((step, i) => {
        const current = running && i === steps.length - 1;
        return (
          <li key={`${i}-${step}`} className="flex items-start gap-2 text-xs">
            {current ? (
              <Loader2 size={13} className="mt-px shrink-0 animate-spin text-accent" />
            ) : (
              <Check size={13} className="mt-px shrink-0 text-emerald-600" />
            )}
            <span className={current ? "text-ink" : "text-soft"}>{step}</span>
            {current && <span className="ml-auto shrink-0 tabular-nums text-faint">{elapsed}s</span>}
          </li>
        );
      })}
    </ol>
  );
}

const examples = [
  "Recent papers on AI and medicine",
  "New videos from AI research channels",
  "NBA headlines from last night",
  "Newsletters about startups in my inbox",
];

export function CreateBlockModal({ onClose }: { onClose: () => void }) {
  const { create, creating } = useBlocks();
  const progress = useBlocks((s) => s.progress);
  const resetProgress = useBlocks((s) => s.resetProgress);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Progress lives in the store so it survives re-renders during a create.
  // That means it also survives the modal closing, so clear it on open;
  // otherwise the previous block's steps greet you on a blank form.
  useEffect(() => {
    resetProgress();
  }, [resetProgress]);

  async function submit() {
    if (!query.trim() || creating) return;
    setError(null);
    const failure = await create(query.trim());
    // On failure the modal stays open with the query intact, so the user can
    // retry or reword instead of retyping.
    if (failure) setError(failure);
    else onClose();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={() => !creating && onClose()}
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

        <AgentProgress steps={progress} running={creating} />

        {error && (
          <div className="mt-3 flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-2.5">
            <AlertCircle size={15} className="mt-0.5 shrink-0 text-red-500" />
            <p className="text-xs leading-relaxed text-soft">{error}</p>
          </div>
        )}

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
            {creating ? "Creating…" : error ? "Try again" : "Create block"}
          </button>
        </div>
      </div>
    </div>
  );
}
