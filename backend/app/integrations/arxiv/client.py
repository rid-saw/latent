"""arXiv API — recent papers for a block query. No auth required."""

import asyncio
import re
import xml.etree.ElementTree as ET

import httpx

from app.models.schemas import ContentItem

API_URL = "https://export.arxiv.org/api/query"
NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

# Words that describe the *ask*, not the topic ("recent papers on ...").
_FILLER = re.compile(
    r"\b(recent|latest|new|papers?|research|studies|study|about|on|in|the|of|for|and|with)\b",
    re.I,
)


def _terms(query: str) -> str:
    cleaned = _FILLER.sub(" ", query)
    words = [w for w in re.split(r"\W+", cleaned) if len(w) > 1]
    if not words:
        return f'all:"{query.strip()}"'
    return " AND ".join(f"all:{w}" for w in words)


async def search_papers(query: str, max_results: int = 5) -> list[ContentItem]:
    params = {
        "search_query": _terms(query),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": max_results,
    }
    # arXiv wants an identifying UA and rate-limits aggressively; retry once.
    async with httpx.AsyncClient(
        timeout=15, headers={"User-Agent": "latent/0.1 (personal dashboard; dev)"}
    ) as client:
        resp = await client.get(API_URL, params=params)
        if resp.status_code == 429:
            await asyncio.sleep(3)
            resp = await client.get(API_URL, params=params)
    resp.raise_for_status()

    items: list[ContentItem] = []
    for entry in ET.fromstring(resp.text).findall("atom:entry", NS):
        link = entry.findtext("atom:id", "", NS)
        title = " ".join(entry.findtext("atom:title", "", NS).split())
        abstract = " ".join(entry.findtext("atom:summary", "", NS).split())
        published = entry.findtext("atom:published", "", NS)[:10]
        primary = entry.find("arxiv:primary_category", NS)
        category = primary.get("term") if primary is not None else "arXiv"
        items.append(
            ContentItem(
                id=link.rsplit("/", 1)[-1],
                title=title,
                url=link,
                source="papers",
                summary=abstract[:220] + ("…" if len(abstract) > 220 else ""),
                meta=f"arXiv · {category} · {published}",
            )
        )
    return items
