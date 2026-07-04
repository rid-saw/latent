"""Google News RSS — query-able news, any topic, no key required."""

import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import httpx

from app.models.schemas import ContentItem

FEED_URL = "https://news.google.com/rss/search"


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


async def search_news(query: str, max_results: int = 5) -> list[ContentItem]:
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(
            FEED_URL,
            params={"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"},
        )
    resp.raise_for_status()

    items: list[ContentItem] = []
    for entry in ET.fromstring(resp.text).iter("item"):
        if len(items) >= max_results:
            break
        title = entry.findtext("title", "")
        link = entry.findtext("link", "")
        source = entry.findtext("source", "")
        try:
            date = parsedate_to_datetime(entry.findtext("pubDate", "")).strftime("%d %b %Y")
        except (ValueError, TypeError):
            date = ""
        # Google News titles end with " - Source"; trim the duplication.
        if source and title.endswith(f" - {source}"):
            title = title[: -len(f" - {source}")]
        items.append(
            ContentItem(
                id=entry.findtext("guid", link) or link,
                title=title,
                url=link,
                source="news",
                summary=_strip_html(entry.findtext("description", ""))[:200] or None,
                meta=" · ".join(p for p in (source, date) if p),
            )
        )
    return items
