import { useEffect, useRef, useState } from "react";
import { GripVertical, Loader2 } from "lucide-react";
import type { Rundown } from "@/types";
import { api } from "@/api/client";
import { useSettings } from "@/stores/settings";

const FRESH_MS = 30 * 60 * 1000; // reuse a briefing younger than 30 min

/** The Rundown as a grid block: draggable, resizable, auto-generated. */
export function RundownCard() {
  const rundownEnabled = useSettings((s) => s.rundownEnabled);
  const [rundown, setRundown] = useState<Rundown | null>(null);
  const [generating, setGenerating] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const autoRan = useRef(false);

  useEffect(() => {
    if (!rundownEnabled || autoRan.current) return;
    autoRan.current = true;
    api
      .getRundown()
      .then(async (latest) => {
        setRundown(latest);
        const fresh =
          latest && Date.now() - new Date(latest.created_at).getTime() < FRESH_MS;
        if (fresh) return;
        setGenerating(true);
        try {
          setRundown(await api.generateRundown());
        } catch (e) {
          const msg = e instanceof Error ? e.message : "";
          setNote(
            msg.includes("No blocks")
              ? "Create a few blocks and the Rundown will write itself."
              : "Couldn't generate a briefing right now.",
          );
        } finally {
          setGenerating(false);
        }
      })
      .catch(() => {});
  }, [rundownEnabled]);

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-line bg-card">
      <header className="block-drag flex cursor-grab items-center gap-2 border-b border-line px-3 py-2 active:cursor-grabbing">
        <GripVertical size={16} className="text-faint" />
        <h3 className="text-sm font-medium">The Rundown</h3>
        {rundown && !generating && (
          <span className="text-xs text-faint">
            {new Date(rundown.created_at).toLocaleString(undefined, {
              month: "short",
              day: "numeric",
              hour: "numeric",
              minute: "2-digit",
            })}
          </span>
        )}
        {generating && (
          <span className="flex items-center gap-1.5 text-xs text-faint">
            <Loader2 size={12} className="animate-spin" /> writing…
          </span>
        )}
      </header>
      <div className="flex-1 overflow-auto p-3">
        {note && <p className="text-xs text-faint">{note}</p>}
        {rundown && (
          <p className="text-sm leading-relaxed text-soft">{rundown.text}</p>
        )}
      </div>
    </div>
  );
}
