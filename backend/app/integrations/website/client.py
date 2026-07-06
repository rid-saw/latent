"""Pinned website blocks: fetch a URL's link-preview metadata (og tags)."""

import re
from urllib.parse import urljoin, urlparse

import httpx

from app.models.schemas import ContentItem

BROWSER_UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
}


def _meta(head: str, *names: str) -> str | None:
    for name in names:
        for pattern in (
            rf'<meta[^>]+(?:property|name)=["\']{name}["\'][^>]+content=["\']([^"\']+)',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']{name}["\']',
        ):
            if m := re.search(pattern, head, re.I):
                return m.group(1).strip()
    return None


async def fetch_site(url: str) -> list[ContentItem]:
    if url.startswith("www."):
        url = f"https://{url}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=BROWSER_UA, follow_redirects=True)
    resp.raise_for_status()
    head = resp.text[:300_000]
    final_url = str(resp.url)
    domain = urlparse(final_url).netloc.removeprefix("www.")

    title = _meta(head, "og:title", "twitter:title")
    if not title and (m := re.search(r"<title[^>]*>([^<]+)</title>", head, re.I)):
        title = m.group(1).strip()
    description = _meta(head, "og:description", "twitter:description", "description")
    image = _meta(head, "og:image", "twitter:image")

    return [
        ContentItem(
            id=final_url,
            title=title or domain,
            url=final_url,
            source="site",
            summary=(description or "")[:220] or None,
            meta=domain,
            thumbnail=urljoin(final_url, image) if image else None,
        )
    ]
