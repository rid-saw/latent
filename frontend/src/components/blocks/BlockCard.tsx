import { GripVertical, RefreshCw, X } from "lucide-react";
import type { Block, SourceKind } from "@/types";
import { useBlocks } from "@/stores/blocks";
import { cn } from "@/lib/cn";

const sourceStyle: Record<SourceKind, string> = {
  papers: "bg-violet-500/15 text-violet-300",
  youtube: "bg-red-500/15 text-red-300",
  gmail: "bg-amber-500/15 text-amber-300",
  news: "bg-sky-500/15 text-sky-300",
  sports: "bg-emerald-500/15 text-emerald-300",
  web: "bg-neutral-500/15 text-neutral-300",
};

export function BlockCard({ block }: { block: Block }) {
  const { refresh, remove } = useBlocks();
  const loading = block.status === "loading";

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-neutral-800 bg-neutral-900">
      <header className="flex items-center gap-2 border-b border-neutral-800 px-3 py-2">
        <button className="block-drag cursor-grab text-neutral-600 hover:text-neutral-400">
          <GripVertical size={16} />
        </button>
        <h3 className="flex-1 truncate text-sm font-medium">{block.title}</h3>
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide",
            sourceStyle[block.source],
          )}
        >
          {block.source}
        </span>
        <button
          onClick={() => refresh(block.id)}
          className="text-neutral-500 hover:text-neutral-200"
          title="Refresh"
        >
          <RefreshCw size={14} className={cn(loading && "animate-spin")} />
        </button>
        <button
          onClick={() => remove(block.id)}
          className="text-neutral-500 hover:text-red-400"
          title="Remove"
        >
          <X size={14} />
        </button>
      </header>

      <div className="flex-1 space-y-2 overflow-auto p-3">
        {block.items.length === 0 ? (
          <p className="text-xs text-neutral-500">No items yet.</p>
        ) : (
          block.items.map((item) => (
            <a
              key={item.id}
              href={item.url}
              target="_blank"
              rel="noreferrer"
              className="block rounded-lg p-2 transition hover:bg-neutral-800"
            >
              <p className="text-sm leading-snug">{item.title}</p>
              {item.meta && (
                <p className="mt-0.5 text-xs text-neutral-500">{item.meta}</p>
              )}
              {item.summary && (
                <p className="mt-1 text-xs text-neutral-400">{item.summary}</p>
              )}
            </a>
          ))
        )}
      </div>
    </div>
  );
}
