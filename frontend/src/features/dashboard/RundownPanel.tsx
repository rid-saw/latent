import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import type { Rundown } from "@/types";
import { api } from "@/api/client";
import { useBlocks } from "@/stores/blocks";
import { usePages } from "@/stores/pages";
import { useSettings } from "@/stores/settings";

const FRESH_MS = 30 * 60 * 1000; // reuse a briefing younger than 30 min

/** The Rundown: fixed strip above the grid, one per page. Hidden when disabled.
 * Only summarizes when the page actually has blocks with content. */
export function RundownPanel() {
  const rundownEnabled = useSettings((s) => s.rundownEnabled);
  const activePageId = usePages((s) => s.activePageId);
  const blockCount = useBlocks((s) => s.blocks.length);
  const loadedPageId = useBlocks((s) => s.loadedPageId);
  const [rundown, setRundown] = useState<Rundown | null>(null);
  const [generating, setGenerating] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const autoRan = useRef(new Set<string>()); // one auto-generation per page

  // Wait until THIS page's blocks are in the store — prevents acting on the
  // previous page's state during a switch.
  const ready = loadedPageId === activePageId;

  useEffect(() => {
    if (!rundownEnabled || !ready) return;
    setRundown(null);
    setNote(null);
    if (blockCount === 0) return; // empty page: no fetching, no generating
    api
      .getRundown(activePageId)
      .then(async (latest) => {
        setRundown(latest);
        const fresh =
          latest && Date.now() - new Date(latest.created_at).getTime() < FRESH_MS;
        if (fresh || autoRan.current.has(activePageId)) return;
        autoRan.current.add(activePageId);
        setGenerating(true);
        try {
          setRundown(await api.generateRundown(activePageId));
        } catch (e) {
          const msg = e instanceof Error ? e.message : "";
          setNote(
            msg.includes("No blocks")
              ? "Your blocks are still empty — refresh one to fill the page."
              : "Couldn't generate a briefing right now.",
          );
        } finally {
          setGenerating(false);
        }
      })
      .catch(() => {});
  }, [rundownEnabled, activePageId, ready, blockCount]);

  if (!rundownEnabled) return null;

  if (ready && blockCount === 0) {
    return (
      <div className="mx-2 mt-2 rounded-xl border border-dashed border-line bg-card/50 p-4">
        <p className="text-sm font-medium">The Rundown</p>
        <p className="mt-1 text-sm text-faint">
          Create a block to get started — once this page has content, your
          briefing will be written here.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-2 mt-2 rounded-xl border border-line bg-card p-4">
      <div className="flex items-center gap-2 text-sm font-medium">
        The Rundown
        {rundown && !generating && (
          <span className="text-xs font-normal text-faint">
            {new Date(rundown.created_at).toLocaleString(undefined, {
              month: "short",
              day: "numeric",
              hour: "numeric",
              minute: "2-digit",
            })}
          </span>
        )}
        {generating && (
          <span className="flex items-center gap-1.5 text-xs font-normal text-faint">
            <Loader2 size={12} className="animate-spin" /> writing…
          </span>
        )}
      </div>
      {note && <p className="mt-2 text-xs text-faint">{note}</p>}
      {rundown && (
        <p className="mt-2 text-sm leading-relaxed text-soft">{rundown.text}</p>
      )}
    </div>
  );
}
