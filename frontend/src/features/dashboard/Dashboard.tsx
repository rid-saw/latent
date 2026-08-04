import { useEffect, useState } from "react";
import {
  GridLayout,
  useContainerWidth,
  verticalCompactor,
  type LayoutItem,
} from "react-grid-layout";
import { AlertCircle, Plus } from "lucide-react";
import type { BlockLayout } from "@/types";
import { useBlocks } from "@/stores/blocks";
import { usePages } from "@/stores/pages";
import { useSettings } from "@/stores/settings";
import { PageIcon } from "@/lib/pageIcons";
import { BlockCard } from "@/components/blocks/BlockCard";
import { DemoBadge } from "@/components/ui/DemoBadge";
import { CreateBlockModal } from "./CreateBlockModal";
import { BriefingPanel } from "./BriefingPanel";


export function Dashboard() {
  const { blocks, loading, loadError, load, applyLayouts } = useBlocks();
  const { pages, activePageId } = usePages();
  const [showCreate, setShowCreate] = useState(false);
  const { width, containerRef, mounted } = useContainerWidth();

  useEffect(() => {
    load();
  }, [load, activePageId]);

  // Quiet auto-refresh: the dashboard stays live without pressing ↻.
  const autoRefreshMins = useSettings((s) => s.autoRefreshMins);
  useEffect(() => {
    if (!autoRefreshMins) return;
    const timer = setInterval(
      () => useBlocks.getState().refreshAll(),
      autoRefreshMins * 60_000,
    );
    return () => clearInterval(timer);
  }, [autoRefreshMins, activePageId]);

  const page = pages.find((p) => p.id === activePageId);

  const layout: LayoutItem[] = blocks.map((b) => ({
    i: b.id,
    x: b.layout.x,
    y: b.layout.y,
    w: b.layout.w,
    h: b.layout.h,
    minW: 3,
    minH: 3,
  }));

  // Commit layout only when the gesture ends — updating state mid-drag makes
  // the controlled grid fight the pointer (snap-backs, broken resize).
  const commitLayout = (current: readonly LayoutItem[]) => {
    const blockLayouts: Record<string, BlockLayout> = {};
    for (const it of current) {
      blockLayouts[it.i] = { x: it.x, y: it.y, w: it.w, h: it.h };
    }
    applyLayouts(blockLayouts);
  };

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <header className="flex items-center justify-between border-b border-line px-6 py-4">
        <h1 className="flex items-center gap-2.5 text-lg font-semibold">
          <PageIcon icon={page?.emoji ?? "file-text"} size={18} />
          {page?.name ?? "Dashboard"}
        </h1>
        <div className="flex items-center gap-2.5">
          <DemoBadge />
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 rounded-lg bg-ink px-3 py-2 text-sm font-medium text-bg hover:opacity-90"
          >
            <Plus size={16} /> Create block
          </button>
        </div>
      </header>

      <BriefingPanel />

      <div
        ref={containerRef}
        className="flex-1 overflow-auto p-2"
        // Kill native HTML5 drags (links/images in cards). Mid-gesture, the
        // hover header loses pointer-events and Chrome re-hit-tests the drag
        // origin, finds the <a> underneath, and starts a link-drag — which
        // silently eats all mouse events and freezes the grid drag.
        onDragStart={(e) => e.preventDefault()}
      >
        {loading ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="animate-pulse rounded-xl border border-line bg-card p-3"
              >
                <div className="mb-3 h-4 w-2/5 rounded bg-surface" />
                <div className="mb-2 h-24 rounded-lg bg-surface" />
                <div className="mb-1.5 h-3 w-4/5 rounded bg-surface" />
                <div className="h-3 w-3/5 rounded bg-surface" />
              </div>
            ))}
          </div>
        ) : loadError && blocks.length === 0 ? (
          <div className="mx-auto mt-24 max-w-md text-center">
            <AlertCircle size={20} className="mx-auto text-red-500" />
            <p className="mt-3 text-sm text-soft">{loadError}</p>
            <button
              onClick={() => load()}
              className="mt-3 rounded-lg border border-line px-3 py-1.5 text-sm text-soft hover:text-ink"
            >
              Try again
            </button>
          </div>
        ) : blocks.length === 0 ? (
          <div className="mt-24 text-center">
            <p className="text-sm text-soft">No blocks yet.</p>
            <button
              onClick={() => setShowCreate(true)}
              className="mt-3 text-sm text-ink underline underline-offset-4"
            >
              Create your first block
            </button>
          </div>
        ) : (
          mounted && (
            // Fixed 24-col grid at every width: shrinking the window scales
            // columns proportionally instead of reflowing (and wrecking) the
            // user's arrangement.
            <GridLayout
              className="layout"
              width={width}
              layout={layout}
              gridConfig={{ cols: 24, rowHeight: 40, margin: [6, 6], containerPadding: [0, 0] }}
              // threshold: accidental sub-10px wiggles don't start a drag.
              dragConfig={{ handle: ".block-drag", threshold: 10 }}
              // Magnetic grid: dragging/resizing into a neighbor pushes it away
              // live, and blocks slide back up the moment space frees.
              compactor={verticalCompactor}
              onDragStop={commitLayout}
              onResizeStop={commitLayout}
            >
              {blocks.map((b) => (
                <div key={b.id}>
                  <BlockCard block={b} />
                </div>
              ))}
            </GridLayout>
          )
        )}
      </div>

      {showCreate && <CreateBlockModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}
