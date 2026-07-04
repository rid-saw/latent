import { useEffect, useRef, useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import type { Rundown } from "@/types";
import { api } from "@/api/client";
import { useSettings } from "@/stores/settings";
import { Switch } from "@/features/settings/SettingsPage";

const FRESH_MS = 30 * 60 * 1000; // reuse a briefing younger than 30 min

/** The Rundown: auto-generated briefing across all blocks, with an on/off toggle. */
export function RundownPanel() {
  const { rundownEnabled, setRundownEnabled } = useSettings();
  const [rundown, setRundown] = useState<Rundown | null>(null);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const autoRan = useRef(false);

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

  useEffect(() => {
    if (!rundownEnabled || autoRan.current) return;
    autoRan.current = true;
    api
      .getRundown()
      .then((latest) => {
        setRundown(latest);
        const fresh =
          latest && Date.now() - new Date(latest.created_at).getTime() < FRESH_MS;
        if (!fresh) generate(); // waiting for the user when the page loads
      })
      .catch(() => {});
  }, [rundownEnabled]);

  if (!rundownEnabled) {
    return (
      <div className="mx-4 mt-4 flex items-center justify-between rounded-xl border border-line bg-card/60 px-4 py-2.5">
        <span className="flex items-center gap-2 text-sm text-faint">
          <Sparkles size={15} /> The Rundown is off
        </span>
        <Switch checked={false} onChange={setRundownEnabled} />
      </div>
    );
  }

  return (
    <div className="mx-4 mt-4 rounded-xl border border-line bg-card p-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Sparkles size={15} className="text-accent" /> The Rundown
          {rundown && (
            <span className="text-xs font-normal text-faint">
              {new Date(rundown.created_at).toLocaleString(undefined, {
                month: "short",
                day: "numeric",
                hour: "numeric",
                minute: "2-digit",
              })}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={generate}
            disabled={generating}
            className="flex items-center gap-2 rounded-lg border border-line px-3 py-1.5 text-xs text-soft hover:border-faint hover:text-ink disabled:opacity-50"
          >
            {generating && <Loader2 size={12} className="animate-spin" />}
            {generating ? "Reading your blocks…" : "Refresh"}
          </button>
          <Switch checked onChange={setRundownEnabled} />
        </div>
      </div>

      {error && <p className="mt-2 text-xs text-red-500">{error}</p>}
      {rundown ? (
        <p className="mt-3 text-sm leading-relaxed text-soft">{rundown.text}</p>
      ) : (
        generating && (
          <p className="mt-3 text-sm text-faint">
            Reading everything you follow and writing your briefing…
          </p>
        )
      )}
    </div>
  );
}
