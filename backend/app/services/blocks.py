"""Block creation/refresh: infer source, route to the right connector.

Mirrors frontend inference (src/api/mock.ts) and layout defaults
(src/lib/layout.ts) — keep in sync until the backend owns persistence.
"""

import logging
import re
import uuid

from fastapi import HTTPException

from app.integrations.espn.client import search_sports
from app.integrations.gmail.client import search_messages
from app.integrations.news.client import search_news
from app.integrations.papers.client import search_papers
from app.integrations.website.client import fetch_site
from app.integrations.youtube.client import search_videos

_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.I)
from app.models.schemas import Block, BlockLayout, ContentItem, SourceKind

_PATTERNS: list[tuple[SourceKind, re.Pattern]] = [
    ("papers", re.compile(r"paper|arxiv|research|study|journal", re.I)),
    ("youtube", re.compile(r"youtube|video|channel", re.I)),
    ("gmail", re.compile(r"email|inbox|newsletter|gmail", re.I)),
    ("sports", re.compile(r"sport|nba|nfl|soccer|football|match", re.I)),
    ("news", re.compile(r"news|headline", re.I)),
]

_SIZES: dict[SourceKind, tuple[int, int]] = {
    "youtube": (4, 6),
    "papers": (6, 7),
    "news": (4, 4),
    "gmail": (3, 4),
    "sports": (3, 3),
    "web": (4, 4),
    "site": (4, 4),
}


def infer_source(query: str) -> SourceKind:
    for kind, pattern in _PATTERNS:
        if pattern.search(query):
            return kind
    return "web"


def title_from(query: str) -> str:
    q = query.strip() or "New block"
    return q[:42] + "…" if len(q) > 42 else q


def default_layout(source: SourceKind) -> BlockLayout:
    w, h = _SIZES[source]
    # Large y -> react-grid-layout compacts the new block to the bottom
    # instead of shoving existing blocks down from the top.
    return BlockLayout(x=0, y=9999, w=w, h=h)


def default_max_items(source: SourceKind) -> int:  # noqa: ARG001 — uniform for now
    return 3


async def fetch_items(query: str, source: SourceKind, max_items: int = 3) -> list[ContentItem]:
    if source == "site":
        m = _URL_RE.search(query)
        return await fetch_site(m.group(0)) if m else []
    if source == "youtube":
        latest = bool(re.search(r"latest|newest|recent|new video", query, re.I))
        return await search_videos(query, max_results=max_items, latest=latest)
    if source == "papers":
        return await search_papers(query, max_results=max_items)
    if source == "gmail":
        return await search_messages(query, max_results=max_items)
    if source == "news":
        return await search_news(query, max_results=max_items)
    if source == "sports":
        return await search_sports(query, max_results=max_items)
    if source == "web":
        return await search_news(query, max_results=max_items)  # keyless generic proxy
    # Other connectors land in later slices; return an honest placeholder.
    return [
        ContentItem(
            id=str(uuid.uuid4()),
            title=f"'{source}' connector coming soon",
            url="https://example.com",
            source=source,
            summary=f"Real {source} content lands in a later slice. YouTube works today.",
            meta="latent · stub",
        )
    ]


async def safe_fetch(
    query: str, source: SourceKind, max_items: int = 3
) -> tuple[list[ContentItem], str]:
    """Fetch items; a connector failure degrades the block, never the request."""
    try:
        return await fetch_items(query, source, max_items), "ready"
    except HTTPException:
        raise  # auth errors (401) should surface as-is
    except Exception:
        logging.exception("fetch_items failed for source=%s", source)
        return [], "error"


async def create_block(query: str) -> Block:
    from app.agents.llm import agents_enabled  # lazy: avoid import cycle

    # A pasted URL means "pin this site" — no routing or LLM needed.
    if _URL_RE.search(query):
        items, status = await safe_fetch(query, "site", 1)
        return Block(
            id=str(uuid.uuid4()),
            title=(items[0].meta or title_from(query)) if items else title_from(query),
            query=query,
            source="site",
            layout=default_layout("site"),
            items=items,
            status=status,
            max_items=1,
        )

    if agents_enabled():
        return await _create_block_agentic(query)

    source = infer_source(query)
    max_items = default_max_items(source)
    items, status = await safe_fetch(query, source, max_items)
    return Block(
        id=str(uuid.uuid4()),
        title=title_from(query),
        query=query,
        source=source,
        layout=default_layout(source),
        items=items,
        status=status,
        max_items=max_items,
    )


async def _create_block_agentic(query: str) -> Block:
    """LangGraph path: supervisor routes, connector fetches, critic verifies."""
    from app.agents.graph import run_block_agent

    try:
        state = await run_block_agent(query)
        source: SourceKind = state["source"]
        max_items = state.get("max_items") or default_max_items(source)
        items = state.get("items") or []
        return Block(
            id=str(uuid.uuid4()),
            title=state.get("title") or title_from(query),
            query=query,
            source=source,
            layout=default_layout(source),
            items=items,
            status="ready",
            max_items=max_items,
        )
    except HTTPException:
        raise
    except Exception:
        logging.exception("agent path failed; falling back to regex inference")
        source = infer_source(query)
        max_items = default_max_items(source)
        items, status = await safe_fetch(query, source, max_items)
        return Block(
            id=str(uuid.uuid4()),
            title=title_from(query),
            query=query,
            source=source,
            layout=default_layout(source),
            items=items,
            status=status,
            max_items=max_items,
        )
