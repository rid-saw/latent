from typing import TypedDict

from app.models.schemas import ContentItem, SourceKind


class BlockAgentState(TypedDict, total=False):
    query: str            # the user's natural-language block prompt
    source: SourceKind    # supervisor's routing decision
    search_terms: str     # connector query: the user's own words if verbatim,
                          # else the supervisor's keywords
    verbatim: bool        # this source searches with the request itself
    location: str         # jobs only: city/region filter
    channel: str          # youtube only: the creator the user named, if any
    title: str            # short block title
    max_items: int        # how many items to show (user-specified or default)
    wants_latest: bool    # newest-first rather than most-relevant
    fields: list[str]     # table blocks only: the column names
    format: str           # web only: how the answer is laid out
    items: list[ContentItem]
