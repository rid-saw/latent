"""The contract. Mirror of frontend/src/types/index.ts — keep in sync."""

from typing import Literal

from pydantic import BaseModel

SourceKind = Literal["youtube", "gmail", "papers", "news", "sports", "web"]
BlockStatus = Literal["idle", "loading", "ready", "error"]


class ContentItem(BaseModel):
    id: str
    title: str
    url: str
    source: SourceKind
    summary: str | None = None
    meta: str | None = None
    thumbnail: str | None = None


class BlockLayout(BaseModel):
    x: int
    y: int
    w: int
    h: int


class Block(BaseModel):
    id: str
    title: str
    query: str
    source: SourceKind
    layout: BlockLayout
    items: list[ContentItem]
    status: BlockStatus
    max_items: int = 3


class CreateBlockRequest(BaseModel):
    query: str
