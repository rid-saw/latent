"""General web search, through whichever provider CLI is already signed in.

This is the connector for anything the specific sources don't cover: how
things work, reviews, background, documentation. No search API key, no
scraping. The CLI runs the search on the provider's own infrastructure and
returns pages it actually visited.

Falls back to Google News RSS when the signed-in CLI can't search, so a
backend without web search is never worse off than before this existed.
"""

import logging
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from app.integrations.news.client import search_news
from app.models.schemas import ContentItem

PROMPT = """Search the web and return the {n} most useful pages for this request:

{query}

Rules:
- Only pages you actually visited in this search. Never invent a URL.
- Prefer primary sources (official sites, documentation, original reporting)
  over aggregators and SEO filler.
- Prefer current pages; say the date in the summary when recency matters.
- summary is one sentence on what the page actually contains.
- If the search returns nothing usable, return an empty list."""


class _Hit(BaseModel):
    title: str
    url: str
    summary: str = ""
    published: str = Field(default="", description="Publication date if the page shows one")


class _Hits(BaseModel):
    results: list[_Hit]


def _site(url: str) -> str:
    """example.com from https://www.example.com/a/b — shown as the item's source."""
    host = urlparse(url).netloc
    return host[4:] if host.startswith("www.") else host


async def _via_cli(query: str, max_results: int) -> list[ContentItem]:
    from app.agents.llm import structured_llm  # lazy: avoid import cycle

    hits = await structured_llm(
        PROMPT.format(query=query, n=max_results), _Hits, web=True
    )
    return [
        ContentItem(
            id=h.url,
            title=h.title,
            url=h.url,
            source="web",
            summary=h.summary or None,
            meta=" · ".join(p for p in (_site(h.url), h.published) if p),
        )
        for h in hits.results
        if h.url.startswith("http")
    ][:max_results]


async def search_web(query: str, max_results: int = 3) -> list[ContentItem]:
    try:
        items = await _via_cli(query, max_results)
    except Exception:
        logging.warning("web search unavailable, falling back to news", exc_info=True)
        return await search_news(query, max_results=max_results)

    # An empty search is a real answer, but news is more useful than a blank card.
    return items or await search_news(query, max_results=max_results)
