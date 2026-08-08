"""Block creation/refresh: infer source, route to the right connector.

Mirrors frontend inference (src/api/mock.ts) and layout defaults
(src/lib/layout.ts) — keep in sync until the backend owns persistence.
"""

import logging
import re
import uuid
from collections.abc import AsyncIterator

from fastapi import HTTPException

from app.services import progress

from app.integrations.espn.client import search_sports
from app.integrations.gmail.client import search_messages
from app.integrations.news.client import search_news
from app.integrations.papers.client import search_papers
from app.integrations.seek.client import search_jobs
from app.integrations.websearch.client import search_web
from app.integrations.website.client import fetch_site
from app.integrations.youtube.client import search_videos

_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.I)
from app.models.schemas import Block, BlockLayout, ContentItem, SourceKind

_PATTERNS: list[tuple[SourceKind, re.Pattern]] = [
    ("papers", re.compile(r"paper|arxiv|research|study|journal", re.I)),
    ("youtube", re.compile(r"youtube|video|channel", re.I)),
    ("gmail", re.compile(r"email|inbox|newsletter|gmail", re.I)),
    ("jobs", re.compile(r"\bjobs?\b|hiring|vacanc|internship|grad program|position|career", re.I)),
    ("sports", re.compile(r"sport|nba|nfl|soccer|football|match", re.I)),
    ("news", re.compile(r"news|headline", re.I)),
]

# v2 grid units: 24 cols, 40px rows (double resolution for granular resizing).
_SIZES: dict[SourceKind, tuple[int, int]] = {
    "youtube": (8, 12),
    "papers": (12, 14),
    "news": (8, 8),
    "gmail": (6, 8),
    "sports": (6, 6),
    "jobs": (8, 10),
    "web": (8, 8),
    "site": (8, 8),
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
    if source == "jobs":
        return await search_jobs(query, max_results=max_items)
    if source == "sports":
        return await search_sports(query, max_results=max_items)
    if source == "web":
        return await search_web(query, max_results=max_items)


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


def placeholder_block(query: str, status: str = "loading") -> Block:
    """The block as it exists before the agent has decided anything.

    Written to the database the moment creation starts, so the prompt is safe
    from everything that follows: a dropped connection, a killed browser, a
    backend restart. The agent then updates this same row rather than
    inserting at the end.

    Source is a keyword guess, good enough to size the card until routing
    replaces it. search_terms stays empty, which is also the signal that a
    retry must re-run the agent rather than refetch — there is nothing to
    refetch until routing has happened.
    """
    source: SourceKind = "site" if _URL_RE.search(query) else infer_source(query)
    return Block(
        id=str(uuid.uuid4()),
        title=title_from(query),
        query=query,
        source=source,
        layout=default_layout(source),
        items=[],
        status=status,  # type: ignore[arg-type]
        max_items=default_max_items(source),
    )


def _block_from(state: dict, query: str, status: str) -> Block:
    source: SourceKind = state.get("source", "web")
    max_items = state.get("max_items") or default_max_items(source)
    return Block(
        id=str(uuid.uuid4()),
        title=state.get("title") or title_from(query),
        query=query,
        search_terms=state.get("search_terms") or "",
        source=source,
        layout=default_layout(source),
        items=(state.get("items") or [])[:max_items],
        status=status,  # type: ignore[arg-type]
        max_items=max_items,
    )


async def create_block_streaming(query: str) -> AsyncIterator[tuple[str, object]]:
    """create_block, narrated. Yields ("progress", line), ("preview", Block)
    once there is something to show, then ("block", Block) when it's final.

    Progress comes from the graph's own node updates, so a line is only shown
    once the step it describes has actually happened.

    The preview exists because results are ready the moment the fetch returns,
    but the critic then spends about as long again judging them. Waiting for
    that doubles the time before anything is on screen, so the raw results go
    out first and the checked version replaces them in place.
    """
    from app.agents.llm import agents_enabled  # lazy: avoid import cycle

    if _URL_RE.search(query) or not agents_enabled():
        # Both are single-fetch paths with nothing to narrate beyond the fetch.
        source = "site" if _URL_RE.search(query) else infer_source(query)
        yield "progress", progress.searching(source, query if source != "site" else "")
        yield "block", await create_block(query)
        return

    from app.agents.graph import MAX_ROUNDS, get_graph

    yield "progress", progress.routing()
    state: dict = {}
    try:
        async for chunk in get_graph().astream(
            {"query": query, "iterations": 0}, stream_mode="updates"
        ):
            for node, update in chunk.items():
                state.update(update)
                source = state.get("source", "web")
                if node == "supervisor":
                    yield "progress", progress.searching(source, state["search_terms"])
                elif node == "fetch":
                    yield "progress", progress.reviewing(source, len(state.get("items") or []))
                    # Show the raw results now rather than after the critic.
                    if state.get("items"):
                        yield "preview", _block_from(state, query, status="loading")
                elif node == "critic" and not state.get("approved"):
                    # Only narrate a refinement that's actually about to happen.
                    if state.get("iterations", 0) < MAX_ROUNDS:
                        yield "progress", progress.refining(state["search_terms"])
    except HTTPException:
        raise
    except Exception:
        logging.exception("agent stream failed; falling back to regex inference")
        yield "block", await create_block(query)
        return

    final = _block_from(state, query, status="ready")
    yield "progress", progress.finishing(final.source, len(final.items))
    yield "block", final


async def _create_block_agentic(query: str) -> Block:
    """LangGraph path: supervisor routes, connector fetches, critic verifies."""
    from app.agents.graph import run_block_agent

    try:
        state = await run_block_agent(query)
        source: SourceKind = state["source"]
        max_items = state.get("max_items") or default_max_items(source)
        # The graph over-fetches so the critic has slack to prune; the block
        # shows only what the user asked for, newest first.
        items = (state.get("items") or [])[:max_items]
        return Block(
            id=str(uuid.uuid4()),
            title=state.get("title") or title_from(query),
            query=query,
            # Persist the supervisor's routing so refreshes reuse it. Without
            # this, every refresh re-searched with the user's raw sentence and
            # quietly replaced good results with junk.
            search_terms=state.get("search_terms") or "",
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
