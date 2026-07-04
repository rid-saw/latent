"""YouTube Data API v3 — search videos for a block query.

For "latest from <channel>" requests, resolve the channel first and list its
uploads newest-first; relevance search can't do that reliably.
"""

import httpx

from app.api.routes.auth import get_access_token
from app.models.schemas import ContentItem

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def _to_item(entry: dict) -> ContentItem:
    vid = entry["id"]["videoId"]
    snip = entry["snippet"]
    thumbs = snip.get("thumbnails", {})
    thumb = (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {}).get("url")
    return ContentItem(
        id=vid,
        title=snip["title"],
        url=f"https://www.youtube.com/watch?v={vid}",
        source="youtube",
        meta=f"{snip['channelTitle']} · {snip['publishedAt'][:10]}",
        thumbnail=thumb,
    )


async def _find_channel(client: httpx.AsyncClient, headers: dict, query: str) -> str | None:
    resp = await client.get(
        SEARCH_URL,
        headers=headers,
        params={"part": "snippet", "q": query, "type": "channel", "maxResults": 1},
    )
    resp.raise_for_status()
    hits = resp.json().get("items", [])
    return hits[0]["id"]["channelId"] if hits else None


async def search_videos(
    query: str, max_results: int = 3, latest: bool = False
) -> list[ContentItem]:
    token = await get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    params: dict = {"part": "snippet", "type": "video", "maxResults": max_results}

    async with httpx.AsyncClient(timeout=15) as client:
        channel_id = await _find_channel(client, headers, query) if latest else None
        if channel_id:
            # The user's actual ask: this channel's newest uploads.
            params |= {"channelId": channel_id, "order": "date"}
        else:
            params |= {"q": query, "order": "date" if latest else "relevance"}
        resp = await client.get(SEARCH_URL, headers=headers, params=params)

    resp.raise_for_status()
    return [_to_item(e) for e in resp.json().get("items", [])]
