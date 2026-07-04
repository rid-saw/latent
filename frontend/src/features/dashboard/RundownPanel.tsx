import { useEffect, useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import type { Rundown } from "@/types";
import { api } from "@/api/client";

/** The Rundown: one agent-written briefing across all blocks. */
export function RundownPanel() {
  const [rundown, setRundown] = useState<Rundown | null>(null);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getRundown().then(setRundown).catch(() => {});
  }, []);

  async function generate() {
    setGenerating(true);
    setError(null);
    try {
      setRundown(await api.generateRundown());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="mx-4 mt-4 rounded-xl border border-neutral-800 bg-gradient-to-br from-neutral-900 to-neutral-900/40 p-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-sm font-medium text-neutral-200">
          <Sparkles size={15} className="text-amber-300" /> The Rundown
          {rundown && (
            <span className="text-xs font-normal text-neutral-500">
              {new Date(rundown.created_at).toLocaleString(undefined, {
                month: "short",
                day: "numeric",
                hour: "numeric",
                minute: "2-digit",
              })}
            </span>
          )}
        </div>
        <button
          onClick={generate}
          disabled={generating}
          className="flex items-center gap-2 rounded-lg border border-neutral-700 px-3 py-1.5 text-xs text-neutral-200 hover:border-neutral-500 disabled:opacity-50"
        >
          {generating && <Loader2 size={12} className="animate-spin" />}
          {generating ? "Reading your blocks…" : rundown ? "Refresh" : "Generate"}
        </button>
      </div>

      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
      {rundown ? (
        <p className="mt-3 text-sm leading-relaxed text-neutral-300">{rundown.text}</p>
      ) : (
        !generating && (
          <p className="mt-3 text-sm text-neutral-500">
            One agent-written briefing across everything you follow. Hit Generate.
          </p>
        )
      )}
    </div>
  );
}
