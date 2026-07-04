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
};

export function BlockCard({ block }: { block: Block }) {
  const { refresh, remove } = useBlocks();
  const loading = block.status === "loading";

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-line bg-card">
      {/* whole header is the drag handle */}
      <header className="block-drag flex cursor-grab items-center gap-2 border-b border-line px-3 py-2 active:cursor-grabbing">
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
          onClick={() => remove(block.id)}
          className="text-faint hover:text-red-500"
          title="Remove"
        >
          <X size={14} />
        </button>
      </header>

      <div className="flex-1 space-y-2 overflow-auto p-3">
        {block.items.length === 0 ? (
          <p className="text-xs text-faint">No items yet.</p>
        ) : (
          block.items.map((item) =>
            item.source === "youtube" ? (
              <VideoCard key={item.id} item={item} />
            ) : item.source === "papers" ? (
              <PaperCard key={item.id} item={item} />
            ) : (
              <LinkPreviewCard key={item.id} item={item} />
            ),
          )
        )}
      </div>
    </div>
  );
}

/** YouTube-style: big 16:9 thumbnail, title + channel below. */
function VideoCard({ item }: { item: ContentItem }) {
  return (
    <a
      href={item.url}
      target="_blank"
      rel="noreferrer"
      className="block overflow-hidden rounded-lg border border-line transition hover:border-faint hover:bg-surface/60"
    >
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
function PaperCard({ item }: { item: ContentItem }) {
  const [imgFailed, setImgFailed] = useState(false);
  return (
    <a
      href={item.url}
      target="_blank"
      rel="noreferrer"
      className="block overflow-hidden rounded-lg border border-line transition hover:border-faint hover:bg-surface/60"
    >
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
      <div className="p-3">
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
function LinkPreviewCard({ item }: { item: ContentItem }) {
  return (
    <a
      href={item.url}
      target="_blank"
      rel="noreferrer"
      className="flex gap-3 overflow-hidden rounded-lg border border-line p-2 transition hover:border-faint hover:bg-surface/60"
    >
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
