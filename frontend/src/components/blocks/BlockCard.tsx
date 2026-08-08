import { useRef, useState } from "react";
import { AlertCircle, GripVertical, Loader2, RefreshCw, X } from "lucide-react";
import type { Block, ContentItem, SourceKind } from "@/types";
import { useBlocks } from "@/stores/blocks";
import { cn } from "@/lib/cn";

const sourceStyle: Record<SourceKind, string> = {
  papers: "bg-violet-500/15 text-violet-700 dark:text-violet-300",
  youtube: "bg-red-500/15 text-red-700 dark:text-red-300",
  gmail: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
  news: "bg-sky-500/15 text-sky-700 dark:text-sky-300",
  sports: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  jobs: "bg-teal-500/15 text-teal-700 dark:text-teal-300",
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

/** `readOnly` is for the preview of a block still being built: it has no
 *  server id yet, so refreshing or deleting it would act on nothing. */
export function BlockCard({ block, readOnly }: { block: Block; readOnly?: boolean }) {
  // `retry` picks refetch or re-route; the card doesn't need to know which.
  const { retry, remove } = useBlocks();
  const freshIds = useBlocks((s) => s.freshIds[block.id]);
  const [confirming, setConfirming] = useState(false);
  const loading = block.status === "loading";
  const isNew = (id: string) => !!freshIds?.includes(id);

  // Reading the block is the point, so the header gets out of the way while
  // you scroll down and comes back the moment you scroll up. Direction rather
  // than position, so you never have to scroll to the top to reach it.
  const [hidden, setHidden] = useState(false);
  const lastY = useRef(0);

  function onScroll(e: React.UIEvent<HTMLDivElement>) {
    const y = e.currentTarget.scrollTop;
    const moved = y - lastY.current;
    if (Math.abs(moved) < 4) return; // ignore jitter and rubber-banding
    lastY.current = y;
    setHidden(y > 4 && moved > 0);
  }

  return (
    <div className="group relative flex h-full flex-col overflow-hidden rounded-xl bg-card">
      {/* Always visible, overlaying the top; the whole bar is the drag handle. */}
      <header
        className={cn(
          "block-drag absolute inset-x-0 top-0 z-20 flex h-9 cursor-grab items-center gap-2",
          "border-b border-line bg-card px-3",
          "transition-transform duration-200 active:cursor-grabbing",
          hidden && "-translate-y-full",
        )}
      >
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
        {!readOnly && (
          <>
            <button
              onClick={() => retry(block.id)}
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
          </>
        )}
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
      {/* pt-9 clears the header at rest; it scrolls away with the content. */}
      <div
        onScroll={onScroll}
        className="min-h-0 flex-1 divide-y divide-line overflow-auto pt-9"
      >
        {loading && block.items.length === 0 ? (
          // Empty and working. Without this it falls through to the empty
          // state and says "Nothing here yet" while the agent is mid-run.
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
            <Loader2 size={16} className="animate-spin text-accent" />
            <p className="text-xs text-faint">Loading…</p>
          </div>
        ) : block.status === "error" && block.items.length === 0 ? (
          <BlockError query={block.query} onRetry={() => retry(block.id)} />
        ) : block.items.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 p-3 text-center">
            <p className="text-xs text-faint">Nothing here yet.</p>
            <button
              onClick={() => retry(block.id)}
              className="text-xs text-soft underline underline-offset-4 hover:text-ink"
            >
              Fetch content
            </button>
          </div>
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

/** Shown when a block's last fetch failed — always with a way out.
 *  The query is echoed because a failed block is saved and reloaded: coming
 *  back to it later, what you asked for is the thing you need to see. */
function BlockError({ query, onRetry }: { query: string; onRetry: () => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 p-4 text-center">
      <AlertCircle size={18} className="text-red-500" />
      <p className="line-clamp-3 text-xs italic leading-relaxed text-faint">"{query}"</p>
      <p className="text-xs leading-relaxed text-soft">
        Couldn't load this one. The source may be busy, or it needs a connected
        account.
      </p>
      <button
        onClick={onRetry}
        className="mt-1 rounded-lg border border-line px-3 py-1.5 text-xs text-soft hover:text-ink"
      >
        Try again
      </button>
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
