"""Block creation/refresh: infer source, route to the right connector.

Mirrors frontend inference (src/api/mock.ts) and layout defaults
(src/lib/layout.ts) — keep in sync until the backend owns persistence.
"""

import re
import uuid

from app.integrations.youtube.client import search_videos
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
    "papers": (4, 4),
    "news": (4, 4),
    "gmail": (3, 4),
    "sports": (3, 3),
    "web": (4, 4),
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
    return BlockLayout(x=0, y=0, w=w, h=h)


async def fetch_items(query: str, source: SourceKind) -> list[ContentItem]:
    if source == "youtube":
        return await search_videos(query)
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


async def create_block(query: str) -> Block:
    source = infer_source(query)
    return Block(
        id=str(uuid.uuid4()),
        title=title_from(query),
        query=query,
        source=source,
        layout=default_layout(source),
        items=await fetch_items(query, source),
        status="ready",
    )
