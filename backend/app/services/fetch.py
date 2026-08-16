"""One fetch, one place, driven by one plan.

Creating a block and refreshing it used to dispatch separately. The graph had
the supervisor's answers in memory and passed them all through; refresh
rebuilt the call from whichever of them happened to have a database column.
Anything without a column was silently dropped on the first refresh — and the
dashboard refreshes on a timer, so a block would be right when you made it and
wrong a few minutes later, with nothing on screen to say why.

It bit three times in a day, wearing a different face each time: a table of
rentals reverting to a list of links, a Fireship block that stopped reading the
channel's upload feed and started web-searching five-year-old videos, and job
searches quietly losing the city they were meant to filter by.

So the supervisor's answers travel together as one plan, both paths run this
function, and a new decision it learns to make is carried without anyone having
to remember to add a column for it.
"""

import re

from app.integrations.espn.client import search_sports
from app.integrations.gmail.client import search_messages
from app.integrations.news.client import search_news
from app.integrations.papers.client import search_papers
from app.integrations.seek.client import search_jobs
from app.integrations.websearch.client import search_web
from app.integrations.website.client import fetch_site
from app.integrations.youtube.client import search_videos
from app.models.schemas import ContentItem

URL_RE = re.compile(r"https?://\S+|www\.\S+", re.I)

# Connectors that take a keyword string and nothing else. youtube, web, jobs
# and site need more than that and are handled directly below.
_CONNECTORS = {
    "papers": search_papers,
    "gmail": search_messages,
    "news": search_news,
    "sports": search_sports,
}


async def fetch_for(plan: dict) -> list[ContentItem]:
    """Fetch what `plan` describes.

    `plan` is the supervisor's answers — source, search_terms, max_items, and
    whichever of channel / location / wants_latest / format / fields apply. A
    block without an agent behind it (a pasted URL, or no CLI installed) fills
    in the same shape by hand, so there is only ever one way to fetch.
    """
    source = plan.get("source") or "web"
    terms = plan.get("search_terms") or ""
    n = plan.get("max_items") or 3

    if source == "site":
        found = URL_RE.search(terms)
        return await fetch_site(found.group(0)) if found else []

    if source == "youtube":
        # `channel` is what keeps this on the upload feed. Lose it and every
        # refresh silently becomes a topic search of whatever the web ranks
        # highest, which is old.
        return await search_videos(
            terms,
            max_results=n,
            latest=plan.get("wants_latest", False),
            channel=plan.get("channel", ""),
            plan=plan,
        )

    if source == "web":
        return await search_web(
            terms,
            max_results=n,
            plan=plan,
            fmt=plan.get("format") or "links",
            fields=plan.get("fields") or [],
        )

    if source == "jobs":
        return await search_jobs(
            terms,
            max_results=n,
            location=plan.get("location", ""),
            latest=plan.get("wants_latest", False),
        )

    if connector := _CONNECTORS.get(source):
        return await connector(terms, max_results=n)
    return []
