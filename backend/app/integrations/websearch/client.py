"""General web search, through whichever provider CLI is already signed in.

This is the connector for anything the specific sources don't cover: how
things work, reviews, background, documentation. No search API key, no
scraping. The CLI runs the search on the provider's own infrastructure and
returns pages it actually visited.

Falls back to Google News RSS when the signed-in CLI can't search, so a
backend without web search is never worse off than before this existed.

This connector is the one place where the user's sentence must survive intact.
Every other source is a keyword index that needs short terms; this one is a
language model, and it can act on the detail the others would choke on. So the
request goes in verbatim and the supervisor's structured answers ride alongside
it as context rather than replacing it.
"""

import logging
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from app.integrations.news.client import search_news
from app.models.schemas import ContentItem

PROMPT = """A personal-dashboard user asked for this, in their own words:

{request}

Read the whole thing. Any constraints, exclusions, amounts or preferences in \
that sentence are part of the request, not noise to be stripped out.
{context}
Return the {n} most useful pages for it.

Rules:
{video_rule}- Only pages you actually visited in this search. Never invent a URL.
- Prefer primary sources (official sites, documentation, original reporting)
  over aggregators and SEO filler.
- Prefer current pages; say the date in the summary when recency matters.
- summary is one sentence on what the page actually contains.
- If the search returns nothing usable, return an empty list."""

# A YouTube topic block has no channel feed to read, so it comes through here.
# Without this the search happily returns listicles *about* videos, which the
# caller then discards as non-videos, leaving an empty block. The instruction
# lives in the wrapper, never appended to what the user wrote.
VIDEO_RULE = (
    "- Return ONLY YouTube video pages — links of the form youtube.com/watch.\n"
    "  Never articles, roundups or listicles about videos.\n"
)


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


_RANKING = {
    True: "the newest ones — recency matters more than relevance",
    False: "the most relevant ones — recency is secondary",
}


def plan_context(plan: dict | None) -> str:
    """The supervisor's structured answers, as context beside the request.

    These are additions, never substitutions: the model still reads the user's
    own sentence above and is free to disagree with anything here.
    """
    if not plan:
        return ""
    rows = []
    for label, key in (
        ("what they're after", "title"),
        ("place", "location"),
        ("channel or creator", "channel"),
    ):
        if plan.get(key):
            rows.append(f"- {label}: {plan[key]}")
    if plan.get("max_items"):
        rows.append(f"- how many they want: {plan['max_items']}")
    rows.append(f"- rank by: {_RANKING[bool(plan.get('wants_latest'))]}")
    return "\nAlso worked out from that same request:\n" + "\n".join(rows) + "\n"


async def _via_cli(
    query: str, max_results: int, plan: dict | None, videos_only: bool
) -> list[ContentItem]:
    from app.agents.llm import structured_llm  # lazy: avoid import cycle

    hits = await structured_llm(
        PROMPT.format(
            request=query,
            n=max_results,
            context=plan_context(plan),
            video_rule=VIDEO_RULE if videos_only else "",
        ),
        _Hits,
        web=True,
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


async def search_web(
    query: str,
    max_results: int = 3,
    *,
    plan: dict | None = None,
    videos_only: bool = False,
) -> list[ContentItem]:
    """`query` is the user's own sentence, not extracted keywords.

    `plan` is the supervisor's structured fields, added as context. Callers
    without one (the no-LLM path, and refresh) simply omit it.
    """
    try:
        items = await _via_cli(query, max_results, plan, videos_only)
    except Exception:
        logging.warning("web search unavailable, falling back to news", exc_info=True)
        return await search_news(query, max_results=max_results)

    # An empty search is a real answer, but news is more useful than a blank card.
    return items or await search_news(query, max_results=max_results)
