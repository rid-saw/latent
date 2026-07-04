import { useEffect, useState } from "react";
import type { Rundown } from "@/types";
import { api } from "@/api/client";
import { useSettings } from "@/stores/settings";

/** The Rundown: written once at backend startup; this panel just displays it.
 * A light poll picks it up if the page loaded while it was still being written. */
export function RundownPanel() {
  const rundownEnabled = useSettings((s) => s.rundownEnabled);
  const [rundown, setRundown] = useState<Rundown | null>(null);

  useEffect(() => {
    if (!rundownEnabled) return;
    let stop = false;
    const fetchLatest = () =>
      api.getRundown().then((r) => !stop && setRundown(r)).catch(() => {});
    fetchLatest();
    const timer = setInterval(fetchLatest, 30_000);
    return () => {
      stop = true;
      clearInterval(timer);
    };
  }, [rundownEnabled]);

  if (!rundownEnabled || !rundown) return null;

  return (
    <div className="mx-4 mt-4 rounded-xl border border-line bg-card p-4">
      <div className="flex items-center gap-2 text-sm font-medium">
        The Rundown
        <span className="text-xs font-normal text-faint">
          {new Date(rundown.created_at).toLocaleString(undefined, {
            month: "short",
            day: "numeric",
            hour: "numeric",
            minute: "2-digit",
          })}
        </span>
      </div>
      <p className="mt-2 text-sm leading-relaxed text-soft">{rundown.text}</p>
    </div>
  );
}
