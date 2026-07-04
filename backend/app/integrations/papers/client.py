"""Papers via OpenAlex (free, keyless, 100k req/day): all publications, not just
arXiv. Falls back to arXiv on failure. Card visuals come from each paper's own
og:image (what link previews use); the frontend renders a generated cover when
a publisher has none."""

import asyncio
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import httpx

from app.integrations.arxiv.client import search_papers as search_arxiv
from app.models.schemas import ContentItem

OPENALEX_URL = "https://api.openalex.org/works"
MAILTO = "dev@latent.local"  # OpenAlex "polite pool" — better rate limits

BROWSER_UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
}
_OG_PATTERNS = (
    re.compile(r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]+content=["\']([^"\']+)', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image|twitter:image)', re.I),
)
_GENERIC_IMAGES = ("arxiv-logo", "favicon", "default-og", "logo-og")


def _abstract(inverted: dict | None) -> str:
    """OpenAlex ships abstracts as {word: [positions]}; rebuild the text."""
    if not inverted:
        return ""
    words: dict[int, str] = {}
    for word, positions in inverted.items():
        for pos in positions:
            words[pos] = word
    return " ".join(words[i] for i in sorted(words))


async def _og_image(client: httpx.AsyncClient, url: str) -> str | None:
    """The page's own link-preview image, if it has a real one."""
    try:
        resp = await client.get(url, headers=BROWSER_UA, follow_redirects=True, timeout=8)
        head = resp.text[:300_000]
        for pattern in _OG_PATTERNS:
            if m := pattern.search(head):
                image = urljoin(str(resp.url), m.group(1))
                if not any(g in image.lower() for g in _GENERIC_IMAGES):
                    return image
        return None
    except Exception:
        return None


async def _add_thumbnails(items: list[ContentItem]) -> None:
    async with httpx.AsyncClient() as client:
        images = await asyncio.gather(*(_og_image(client, it.url) for it in items))
    for item, image in zip(items, images):
        item.thumbnail = image


async def _from_openalex(query: str, max_results: int) -> list[ContentItem]:
    since = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")
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

    items: list[ContentItem] = []
    for w in (resp.json().get("results") or [])[:max_results]:
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
            )
        )
    return items


async def search_papers(query: str, max_results: int = 3) -> list[ContentItem]:
    try:
        items = await _from_openalex(query, max_results)
    except Exception:
        items = []
    if not items:
        items = await search_arxiv(query, max_results)
    await _add_thumbnails(items)
    return items
