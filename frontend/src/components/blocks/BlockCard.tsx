import { useState } from "react";
import { GripVertical, RefreshCw, X } from "lucide-react";
import type { Block, ContentItem, SourceKind } from "@/types";
import { useBlocks } from "@/stores/blocks";
import { cn } from "@/lib/cn";

const sourceStyle: Record<SourceKind, string> = {
  papers: "bg-violet-500/15 text-violet-700 dark:text-violet-300",
  youtube: "bg-red-500/15 text-red-700 dark:text-red-300",
  gmail: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
  news: "bg-sky-500/15 text-sky-700 dark:text-sky-300",
  sports: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  web: "bg-stone-500/15 text-stone-600 dark:text-stone-300",
  site: "bg-indigo-500/15 text-indigo-700 dark:text-indigo-300",
};

function NewBadge() {
  return (
    <span className="absolute right-1.5 top-1.5 z-10 rounded-full bg-accent px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-white shadow">
      new
    </span>
  );
}

export function BlockCard({ block }: { block: Block }) {
  const { refresh, remove } = useBlocks();
  const freshIds = useBlocks((s) => s.freshIds[block.id]);
  const [confirming, setConfirming] = useState(false);
  const loading = block.status === "loading";
  const isNew = (id: string) => !!freshIds?.includes(id);

  return (
    <div className="group relative flex h-full flex-col overflow-hidden rounded-xl bg-card">
      {/* header overlays the top and appears on hover; whole header drags */}
      <header className="block-drag pointer-events-none absolute inset-x-0 top-0 z-20 flex cursor-grab items-center gap-2 border-b border-line bg-card/95 px-3 py-2 opacity-0 backdrop-blur-sm transition-opacity duration-150 active:cursor-grabbing group-hover:pointer-events-auto group-hover:opacity-100">
        <GripVertical size={16} className="text-faint" />
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
          className="text-faint hover:text-ink"
          title="Refresh"
        >
          <RefreshCw size={14} className={cn(loading && "animate-spin")} />
        </button>
        <button
          onClick={() => setConfirming(true)}
          className="text-faint hover:text-red-500"
          title="Remove"
        >
          <X size={14} />
        </button>
      </header>

      {confirming && (
        <div className="absolute inset-0 z-30 flex flex-col items-center justify-center gap-3 bg-card/95 p-4 backdrop-blur-sm">
          <p className="text-sm font-medium">Delete this block?</p>
          <div className="flex gap-2">
            <button
              onClick={() => setConfirming(false)}
              className="rounded-lg border border-line px-3 py-1.5 text-xs text-soft hover:text-ink"
            >
              Cancel
            </button>
            <button
              onClick={() => remove(block.id)}
              className="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700"
            >
              Delete
            </button>
          </div>
        </div>
      )}

      {/* Edge-to-edge content: no card border or padding; items separated by
          hairline dividers and clipped by the container's rounded corners. */}
      <div className="min-h-0 flex-1 divide-y divide-line overflow-auto">
        {block.items.length === 0 ? (
          <p className="p-3 text-xs text-faint">No items yet.</p>
        ) : (
          block.items.map((item) =>
            item.source === "youtube" ? (
              <VideoCard key={item.id} item={item} isNew={isNew(item.id)} />
            ) : item.source === "papers" || item.source === "site" ? (
              <PaperCard key={item.id} item={item} isNew={isNew(item.id)} />
            ) : (
              <LinkPreviewCard key={item.id} item={item} isNew={isNew(item.id)} />
            ),
          )
        )}
      </div>
    </div>
  );
}

/** YouTube-style: big 16:9 thumbnail, title + channel below. */
function VideoCard({ item, isNew }: { item: ContentItem; isNew?: boolean }) {
  return (
    <a
      href={item.url}
      target="_blank"
      rel="noreferrer"
      className="relative block overflow-hidden transition hover:bg-surface/60"
    >
      {isNew && <NewBadge />}
      {item.thumbnail && (
        <img
          src={item.thumbnail}
          alt=""
          loading="lazy"
          className="aspect-video w-full object-cover"
        />
      )}
      <div className="p-2">
        <p className="line-clamp-2 text-sm leading-snug">{item.title}</p>
        {item.meta && (
          <p className="mt-0.5 text-xs text-faint">{item.meta}</p>
        )}
      </div>
    </a>
  );
}

/** Deterministic gradient cover for papers whose publisher has no usable image. */
function PaperCover({ item }: { item: ContentItem }) {
  const venue = (item.meta || "Paper").split("·")[0].trim();
  let hash = 0;
  for (const ch of venue + item.title) hash = (hash * 31 + ch.charCodeAt(0)) % 360;
  const monogram = venue
    .split(/\s+/)
    .slice(0, 3)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
  return (
    <div
      className="flex aspect-[2/1] w-full items-center justify-center border-b border-line"
      style={{
        background: `linear-gradient(135deg, hsl(${hash} 30% 68%), hsl(${(hash + 50) % 360} 28% 42%))`,
      }}
    >
      <span className="font-serif text-4xl font-semibold tracking-widest text-white/75">
        {monogram}
      </span>
    </div>
  );
}

/** Papers: large visual card — publisher og:image, or a generated cover. */
function PaperCard({ item, isNew }: { item: ContentItem; isNew?: boolean }) {
  const [imgFailed, setImgFailed] = useState(false);
  return (
    <a
      href={item.url}
      target="_blank"
      rel="noreferrer"
      className="relative block overflow-hidden transition hover:bg-surface/60"
    >
      {isNew && <NewBadge />}
      {item.thumbnail && !imgFailed ? (
        <img
          src={item.thumbnail}
          alt=""
          loading="lazy"
          onError={() => setImgFailed(true)}
          className="aspect-[2/1] w-full border-b border-line object-cover object-top"
        />
      ) : (
        <PaperCover item={item} />
      )}
      <div className="p-2.5">
        {item.meta && (
          <p className="truncate text-[11px] font-medium uppercase tracking-wide text-accent">
            {item.meta}
          </p>
        )}
        <p className="mt-1 line-clamp-2 text-base font-medium leading-snug">
          {item.title}
        </p>
        {item.summary && (
          <p className="mt-1.5 line-clamp-2 text-xs leading-relaxed text-soft">
            {item.summary}
          </p>
        )}
      </div>
    </a>
  );
}

/** Link-preview style (WhatsApp/OG): thumbnail beside title, source name, summary. */
function LinkPreviewCard({ item, isNew }: { item: ContentItem; isNew?: boolean }) {
  return (
    <a
      href={item.url}
      target="_blank"
      rel="noreferrer"
      className="relative flex gap-3 overflow-hidden p-2 transition hover:bg-surface/60"
    >
      {isNew && <NewBadge />}
      {item.thumbnail && (
        <img
          src={item.thumbnail}
          alt=""
          loading="lazy"
          className="h-16 w-24 shrink-0 rounded-md object-cover"
        />
      )}
      <div className="min-w-0">
        {item.meta && (
          <p className="truncate text-[11px] font-medium uppercase tracking-wide text-faint">
            {item.meta}
          </p>
        )}
        <p className="line-clamp-2 text-sm leading-snug">{item.title}</p>
        {item.summary && (
          <p className="mt-0.5 line-clamp-2 text-xs text-soft">
            {item.summary}
          </p>
        )}
      </div>
    </a>
  );
}
