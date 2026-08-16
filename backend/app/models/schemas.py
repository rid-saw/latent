"""The contract. Mirror of frontend/src/types/index.ts — keep in sync."""

from typing import Literal

from pydantic import BaseModel

SourceKind = Literal["youtube", "gmail", "papers", "news", "sports", "jobs", "web", "site"]

# How a block's answer is laid out. Only web varies: every other source
# returns things that are pages, so "links" is the only shape that fits them.
BlockFormat = Literal["links", "text", "bullets", "steps", "table", "stat", "code"]
BlockStatus = Literal["idle", "loading", "ready", "error"]


class ContentItem(BaseModel):
    id: str
    title: str
    # The page this came from. Empty when the item is a thing rather than a
    # page — a sale, a fact, a slang term — in which case it still carries the
    # page it was read from, as evidence, wherever one exists.
    url: str = ""
    source: SourceKind
    summary: str | None = None
    meta: str | None = None
    thumbnail: str | None = None
    # Named values about this item: {"price": "A$2.4M", "citations": "514"}.
    # Two ways of filling it — connectors with known fields (papers, jobs,
    # gmail) set them directly; a web search is told which fields to return by
    # the supervisor, because what belongs on the row depends on the request.
    fields: dict[str, str] | None = None
    # The answer itself, when it is longer than a title: the prose of an
    # explanation, the lines of a code snippet. Everything else fits in the
    # title, or is a row of its own.
    body: str | None = None


class BlockLayout(BaseModel):
    x: int
    y: int
    w: int
    h: int


class Page(BaseModel):
    id: str
    name: str
    emoji: str = "file-text"  # lucide icon name, or a legacy emoji character


class Block(BaseModel):
    id: str
    page_id: str = "default"
    title: str
    query: str  # what the user typed, verbatim
    # Everything the supervisor decided, kept whole: search_terms, max_items,
    # and whichever of channel / location / wants_latest / format / fields
    # apply. Stored as one thing rather than picked apart into columns because
    # every decision that lacked a column was dropped on the first refresh —
    # a channel block reverting to a web search, a table reverting to links, a
    # Melbourne job search losing Melbourne.
    plan: dict = {}
    source: SourceKind
    layout: BlockLayout
    items: list[ContentItem]
    status: BlockStatus
    max_items: int = 3


class CreateBlockRequest(BaseModel):
    query: str
    page_id: str = "default"


class CreatePageRequest(BaseModel):
    name: str
    emoji: str = "file-text"


class UpdatePageRequest(BaseModel):
    name: str | None = None
    emoji: str | None = None
