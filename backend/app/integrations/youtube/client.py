"""YouTube Data API v3 — search recent videos for a block query."""

import httpx

from app.api.routes.auth import get_access_token
from app.models.schemas import ContentItem

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


async def search_videos(query: str, max_results: int = 3) -> list[ContentItem]:
    token = await get_access_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            SEARCH_URL,
            headers={"Authorization": f"Bearer {token}"},
            params={
                "part": "snippet",
                "q": query,
                "type": "video",
                "order": "relevance",
                "maxResults": max_results,
            },
        )
    resp.raise_for_status()

    items: list[ContentItem] = []
    for entry in resp.json().get("items", []):
        vid = entry["id"]["videoId"]
        snip = entry["snippet"]
        thumbs = snip.get("thumbnails", {})
        thumb = (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {}).get("url")
        items.append(
            ContentItem(
                id=vid,
                title=snip["title"],
                url=f"https://www.youtube.com/watch?v={vid}",
                source="youtube",
                meta=f"{snip['channelTitle']} · {snip['publishedAt'][:10]}",
                thumbnail=thumb,
            )
        )
    return items
