import { useEffect, useState } from "react";
import {
  ResponsiveGridLayout,
  noCompactor,
  useContainerWidth,
  type LayoutItem,
} from "react-grid-layout";
import { Plus } from "lucide-react";
import type { BlockLayout } from "@/types";
import { useBlocks } from "@/stores/blocks";
import { useSettings } from "@/stores/settings";
import { BlockCard } from "@/components/blocks/BlockCard";
import { CreateBlockModal } from "./CreateBlockModal";
import { RundownCard } from "./RundownPanel";

// Free-form: no auto-compaction, blocks stay where dropped, no overlap.
const freeform = { ...noCompactor, preventCollision: true };

const RUNDOWN_ID = "__rundown__";

const intersects = (a: BlockLayout, b: BlockLayout) =>
  a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;

export function Dashboard() {
  const { blocks, loading, load, applyLayouts } = useBlocks();
  const { rundownEnabled, rundownLayout, setRundownLayout } = useSettings();
  const [showCreate, setShowCreate] = useState(false);
  const { width, containerRef, mounted } = useContainerWidth();

  useEffect(() => {
    load();
  }, [load]);

  // One-time on load: if the rundown block overlaps existing blocks (e.g. it was
  // just introduced), nudge the colliding blocks below it.
  useEffect(() => {
    if (loading || !rundownEnabled) return;
    const shifted: Record<string, BlockLayout> = {};
    for (const b of blocks) {
      if (intersects(b.layout, rundownLayout)) {
        shifted[b.id] = { ...b.layout, y: rundownLayout.y + rundownLayout.h };
      }
    }
    if (Object.keys(shifted).length) applyLayouts(shifted);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading]);

  const layout: LayoutItem[] = [
    ...(rundownEnabled
      ? [{ i: RUNDOWN_ID, ...rundownLayout, minW: 3, minH: 2 }]
      : []),
    ...blocks.map((b) => ({
      i: b.id,
      x: b.layout.x,
      y: b.layout.y,
      w: b.layout.w,
      h: b.layout.h,
      minW: 2,
      minH: 2,
    })),
  ];

  // Commit layout only when the gesture ends — updating state mid-drag makes
  // the controlled grid fight the pointer (snap-backs, broken resize).
  const commitLayout = (current: readonly LayoutItem[]) => {
    const blockLayouts: Record<string, BlockLayout> = {};
    for (const it of current) {
      const l = { x: it.x, y: it.y, w: it.w, h: it.h };
      if (it.i === RUNDOWN_ID) setRundownLayout(l);
      else blockLayouts[it.i] = l;
    }
    applyLayouts(blockLayouts);
  };

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <header className="flex items-center justify-between border-b border-line px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold">Your rundown</h1>
          <p className="text-sm text-faint">
            Everything you're keeping up with, in one view.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-lg bg-ink px-3 py-2 text-sm font-medium text-bg hover:opacity-90"
        >
          <Plus size={16} /> Create block
        </button>
      </header>

      <div ref={containerRef} className="flex-1 overflow-auto p-4">
        {loading ? (
          <p className="p-6 text-sm text-faint">Loading…</p>
        ) : blocks.length === 0 && !rundownEnabled ? (
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
            <ResponsiveGridLayout
              className="layout"
              width={width}
              layouts={{ lg: layout, md: layout, sm: layout }}
              breakpoints={{ lg: 1200, md: 800, sm: 0 }}
              cols={{ lg: 12, md: 8, sm: 4 }}
              rowHeight={80}
              dragConfig={{ handle: ".block-drag" }}
              compactor={freeform}
              onDragStop={commitLayout}
              onResizeStop={commitLayout}
            >
              {rundownEnabled && (
                <div key={RUNDOWN_ID}>
                  <RundownCard />
                </div>
              )}
              {blocks.map((b) => (
                <div key={b.id}>
                  <BlockCard block={b} />
                </div>
              ))}
            </ResponsiveGridLayout>
          )
        )}
      </div>

      {showCreate && <CreateBlockModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}
