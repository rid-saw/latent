from typing import TypedDict

from app.models.schemas import ContentItem, SourceKind


class BlockAgentState(TypedDict, total=False):
    query: str            # the user's natural-language block prompt
    source: SourceKind    # supervisor's routing decision
    search_terms: str     # supervisor/critic-refined terms for the connector
    location: str         # jobs only: city/region filter
    title: str            # short block title
    max_items: int        # how many items to show (user-specified or default)
    wants_latest: bool    # newest-first rather than most-relevant
    items: list[ContentItem]
    approved: bool        # critic verdict
    iterations: int       # fetch rounds completed (reflection loop guard)
