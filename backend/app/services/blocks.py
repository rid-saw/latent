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

from app.services.fetch import URL_RE as _URL_RE, fetch_for
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


async def safe_fetch(plan: dict) -> tuple[list[ContentItem], str]:
    """Fetch what `plan` describes; a connector failure degrades the block,
    never the request."""
    try:
        return await fetch_for(plan), "ready"
    except HTTPException:
        raise  # auth errors (401) should surface as-is
    except Exception:
        logging.exception("fetch failed for source=%s", plan.get("source"))
        return [], "error"


def plan_without_an_agent(query: str) -> dict:
    """The plan a block gets when no agent produced one.

    A pasted URL needs no routing, and a machine with no CLI installed has no
    agent to do it. Both still fetch through the same dispatcher, so both need
    a plan — the difference is that a regex filled it in.
    """
    if URL := _URL_RE.search(query):
        return {"source": "site", "search_terms": URL.group(0), "max_items": 1}
    source = infer_source(query)
    return {
        "source": source,
        "search_terms": query,
        "max_items": default_max_items(source),
    }


async def create_block(query: str) -> Block:
    from app.agents.llm import agents_enabled  # lazy: avoid import cycle

    # A pasted URL means "pin this site" — no routing or LLM needed. Neither
    # is there anything to route with when no CLI is installed.
    if agents_enabled() and not _URL_RE.search(query):
        return await _create_block_agentic(query)

    plan = plan_without_an_agent(query)
    items, status = await safe_fetch(plan)
    source: SourceKind = plan["source"]
    pinned = source == "site" and items
    return Block(
        id=str(uuid.uuid4()),
        title=(items[0].meta or title_from(query)) if pinned else title_from(query),
        query=query,
        plan=plan,
        source=source,
        layout=default_layout(source),
        items=items,
        status=status,
        max_items=plan["max_items"],
    )


def placeholder_block(query: str, status: str = "loading") -> Block:
    """The block as it exists before the agent has decided anything.

    Written to the database the moment creation starts, so the prompt is safe
    from everything that follows: a dropped connection, a killed browser, a
    backend restart. The agent then updates this same row rather than
    inserting at the end.

    Source is a keyword guess, good enough to size the card until routing
    replaces it. The plan stays empty, which is also the signal that a retry
    must re-run the agent rather than refetch — there is nothing to refetch
    until routing has happened.
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


# The agent's working state minus the parts that are not decisions: the
# original prompt, and the results themselves.
_NOT_A_DECISION = {"query", "items"}


def _block_from(state: dict, query: str, status: str) -> Block:
    source: SourceKind = state.get("source", "web")
    max_items = state.get("max_items") or default_max_items(source)
    # Everything the supervisor decided, kept whole. Copying named fields out
    # one at a time is what let a refresh lose the ones nobody remembered.
    plan = {k: v for k, v in state.items() if k not in _NOT_A_DECISION}
    plan.setdefault("source", source)
    plan.setdefault("max_items", max_items)
    return Block(
        id=str(uuid.uuid4()),
        title=state.get("title") or title_from(query),
        query=query,
        plan=plan,
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

    The preview goes out the moment the fetch returns, ahead of the saved
    block, so the card has something on it as early as possible.
    """
    from app.agents.llm import agents_enabled  # lazy: avoid import cycle

    if _URL_RE.search(query) or not agents_enabled():
        # Both are single-fetch paths with nothing to narrate beyond the fetch.
        source = "site" if _URL_RE.search(query) else infer_source(query)
        yield "progress", progress.searching(source, query if source != "site" else "")
        yield "block", await create_block(query)
        return

    from app.agents.graph import get_graph

    yield "progress", progress.routing()
    state: dict = {}
    try:
        async for chunk in get_graph().astream(
            {"query": query}, stream_mode="updates"
        ):
            for node, update in chunk.items():
                state.update(update)
                if node == "supervisor":
                    yield "progress", progress.searching(
                        state.get("source", "web"), state["search_terms"]
                    )
                elif node == "fetch" and state.get("items"):
                    yield "preview", _block_from(state, query, status="loading")
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
    """LangGraph path: the supervisor routes, the connector fetches."""
    from app.agents.graph import run_block_agent

    try:
        return _block_from(await run_block_agent(query), query, status="ready")
    except HTTPException:
        raise
    except Exception:
        logging.exception("agent path failed; falling back to keyword routing")
        plan = plan_without_an_agent(query)
        items, status = await safe_fetch(plan)
        source: SourceKind = plan["source"]
        return Block(
            id=str(uuid.uuid4()),
            title=title_from(query),
            query=query,
            plan=plan,
            source=source,
            layout=default_layout(source),
            items=items,
            status=status,
            max_items=plan["max_items"],
        )
