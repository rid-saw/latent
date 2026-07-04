import { useEffect, useState } from "react";
import { Responsive, WidthProvider, type Layout } from "react-grid-layout";
import { Plus } from "lucide-react";
import { useBlocks } from "@/stores/blocks";
import { BlockCard } from "@/components/blocks/BlockCard";
import { CreateBlockModal } from "./CreateBlockModal";
import { RundownPanel } from "./RundownPanel";

const Grid = WidthProvider(Responsive);

export function Dashboard() {
  const { blocks, loading, load, applyLayouts } = useBlocks();
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    load();
  }, [load]);

  const layout: Layout[] = blocks.map((b) => ({
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
  const commitLayout = (current: Layout[]) =>
    applyLayouts(
      Object.fromEntries(
        current.map((it) => [it.i, { x: it.x, y: it.y, w: it.w, h: it.h }]),
      ),
    );

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <header className="flex items-center justify-between border-b border-neutral-800 px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold">Your rundown</h1>
          <p className="text-sm text-neutral-500">
            Everything you're keeping up with, in one view.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-lg bg-neutral-100 px-3 py-2 text-sm font-medium text-neutral-900 hover:bg-white"
        >
          <Plus size={16} /> Create block
        </button>
      </header>

      <RundownPanel />

      <div className="flex-1 overflow-auto p-4">
        {loading ? (
          <p className="p-6 text-sm text-neutral-500">Loading…</p>
        ) : blocks.length === 0 ? (
          <div className="mt-24 text-center">
            <p className="text-sm text-neutral-400">No blocks yet.</p>
            <button
              onClick={() => setShowCreate(true)}
              className="mt-3 text-sm text-neutral-200 underline underline-offset-4"
            >
              Create your first block
            </button>
          </div>
        ) : (
          <Grid
            className="layout"
            layouts={{ lg: layout, md: layout, sm: layout }}
            breakpoints={{ lg: 1200, md: 800, sm: 0 }}
            cols={{ lg: 12, md: 8, sm: 4 }}
            rowHeight={80}
            draggableHandle=".block-drag"
            onDragStop={commitLayout}
            onResizeStop={commitLayout}
          >
            {blocks.map((b) => (
              <div key={b.id}>
                <BlockCard block={b} />
              </div>
            ))}
          </Grid>
        )}
      </div>

      {showCreate && <CreateBlockModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}
