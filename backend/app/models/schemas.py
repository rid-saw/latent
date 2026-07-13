"""The contract. Mirror of frontend/src/types/index.ts — keep in sync."""

from typing import Literal

from pydantic import BaseModel

SourceKind = Literal["youtube", "gmail", "papers", "news", "sports", "jobs", "web", "site"]
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


class Page(BaseModel):
    id: str
    name: str
    emoji: str = "file-text"  # lucide icon name, or a legacy emoji character


class Block(BaseModel):
    id: str
    page_id: str = "default"
    title: str
    query: str
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
