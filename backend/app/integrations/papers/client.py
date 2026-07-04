"""Papers via OpenAlex (free, keyless, 100k req/day): all publications, not just
arXiv. Falls back to arXiv on failure. Card thumbnails are live page snapshots
via image.thum.io (free, keyless)."""

from datetime import datetime, timedelta, timezone

import httpx

from app.integrations.arxiv.client import search_papers as search_arxiv
from app.models.schemas import ContentItem

OPENALEX_URL = "https://api.openalex.org/works"
MAILTO = "dev@latent.local"  # OpenAlex "polite pool" — better rate limits


def _snapshot(url: str) -> str:
    return f"https://image.thum.io/get/width/640/crop/400/{url}"


def _abstract(inverted: dict | None) -> str:
    """OpenAlex ships abstracts as {word: [positions]}; rebuild the text."""
    if not inverted:
        return ""
    words: dict[int, str] = {}
    for word, positions in inverted.items():
        for pos in positions:
            words[pos] = word
    return " ".join(words[i] for i in sorted(words))


async def search_papers(query: str, max_results: int = 3) -> list[ContentItem]:
    since = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                OPENALEX_URL,
                params={
                    "search": query,
                    "filter": f"from_publication_date:{since}",
                    "per-page": max_results,
                    "mailto": MAILTO,
                },
            )
        resp.raise_for_status()
        works = resp.json().get("results") or []
    except Exception:
        return await search_arxiv(query, max_results)

    items: list[ContentItem] = []
    for w in works[:max_results]:
        loc = w.get("primary_location") or {}
        url = loc.get("landing_page_url") or w.get("doi") or ""
        title = w.get("display_name")
        if not title or not url:
            continue
        venue = (loc.get("source") or {}).get("display_name") or "Preprint"
        abstract = _abstract(w.get("abstract_inverted_index"))
        items.append(
            ContentItem(
                id=str(w.get("id") or url),
                title=title,
                url=url,
                source="papers",
                summary=(abstract[:220] + "…") if len(abstract) > 220 else abstract or None,
                meta=f"{venue} · {w.get('publication_date', '')}",
                thumbnail=_snapshot(url),
            )
        )
    return items if items else await search_arxiv(query, max_results)
