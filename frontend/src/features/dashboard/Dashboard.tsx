import { useEffect, useState } from "react";
import {
  ResponsiveGridLayout,
  noCompactor,
  useContainerWidth,
  type LayoutItem,
} from "react-grid-layout";
import { Plus } from "lucide-react";
import { useBlocks } from "@/stores/blocks";
import { BlockCard } from "@/components/blocks/BlockCard";
import { CreateBlockModal } from "./CreateBlockModal";
import { RundownPanel } from "./RundownPanel";

// Free-form: no auto-compaction, blocks stay where dropped, no overlap.
const freeform = { ...noCompactor, preventCollision: true };

export function Dashboard() {
  const { blocks, loading, load, applyLayouts } = useBlocks();
  const [showCreate, setShowCreate] = useState(false);
  const { width, containerRef, mounted } = useContainerWidth();

  useEffect(() => {
    load();
  }, [load]);

  const layout: LayoutItem[] = blocks.map((b) => ({
    i: b.id,
    x: b.layout.x,
    y: b.layout.y,
    w: b.layout.w,
    h: b.layout.h,
    minW: 2,
    minH: 2,
  }));

  // Commit layout only when the gesture ends — updating state mid-drag makes
  // the controlled grid fight the pointer (snap-backs, broken resize).
  const commitLayout = (current: readonly LayoutItem[]) =>
    applyLayouts(
      Object.fromEntries(
        current.map((it) => [it.i, { x: it.x, y: it.y, w: it.w, h: it.h }]),
      ),
    );

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

      <RundownPanel />

      <div ref={containerRef} className="flex-1 overflow-auto p-4">
        {loading ? (
          <p className="p-6 text-sm text-faint">Loading…</p>
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
