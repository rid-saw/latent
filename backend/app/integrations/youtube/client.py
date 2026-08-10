"""YouTube without an account, a key, or a Google Cloud project.

Two public surfaces do everything the Data API was being used for:

  channel feeds  every channel publishes its recent uploads as RSS, with
                 title, date and thumbnail — the whole card, keyless
  oembed         title, channel name and thumbnail for any video id, keyless

The Data API needed `youtube.readonly`, which is permission to read the user's
account — and latent never read it. It only ever searched public videos. So
the consent bought nothing and, because it was requested alongside Gmail, cost
the user read access to their inbox to watch videos.

Topic searches have no feed to read, so those go through web search (the
user's own CLI) filtered to youtube.com, with oembed filling in the details.
"""

import asyncio
import logging
import re
from html import unescape
from urllib.parse import quote

import httpx

from app.models.schemas import ContentItem

FEED_URL = "https://www.youtube.com/feeds/videos.xml"
OEMBED_URL = "https://www.youtube.com/oembed"
WATCH_RE = re.compile(r"youtube\.com/watch\?v=([\w-]{11})|youtu\.be/([\w-]{11})", re.I)

BROWSER_UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
}

# The channel page mentions several channel ids (related channels, shelves),
# and the first one is often not the page's own — resolving @fireship that way
# returns Beyond Fireship. The canonical link is the page saying who it is.
_CANONICAL_RE = re.compile(
    r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[\w-]+)"', re.I
)

_ENTRY_RE = re.compile(r"<entry>(.*?)</entry>", re.S)

# Ceiling on pages requested for a topic search. Enough that the non-video
# results can be filtered out and still leave the block full; low enough that
# the search isn't scraping the bottom of the barrel for pages nobody reads.
MAX_WEB_PAGES = 12


def _tag(entry: str, name: str) -> str:
    m = re.search(rf"<{name}[^>]*>(.*?)</{name}>", entry, re.S)
    return unescape(m.group(1)).strip() if m else ""


def thumbnail_for(video_id: str) -> str:
    """Thumbnails are at a fixed path, so an id is enough to build one."""
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"


async def _channel_id(client: httpx.AsyncClient, channel: str) -> str | None:
    """A channel name or @handle -> its id, by asking the channel page."""
    handle = channel.strip().lstrip("@").replace(" ", "")
    resp = await client.get(
        f"https://www.youtube.com/@{quote(handle)}",
        headers=BROWSER_UA,
        follow_redirects=True,
    )
    if resp.status_code != 200:
        return None
    found = _CANONICAL_RE.search(resp.text)
    return found.group(1) if found else None


async def _channel_uploads(
    client: httpx.AsyncClient, channel: str, max_results: int
) -> list[ContentItem]:
    channel_id = await _channel_id(client, channel)
    if not channel_id:
        return []
    resp = await client.get(FEED_URL, params={"channel_id": channel_id})
    if resp.status_code != 200:
        return []

    items: list[ContentItem] = []
    for entry in _ENTRY_RE.findall(resp.text)[:max_results]:
        video_id = _tag(entry, "yt:videoId")
        if not video_id:
            continue
        published = _tag(entry, "published")[:10]
        author = _tag(entry, "name")
        items.append(
            ContentItem(
                id=video_id,
                title=_tag(entry, "media:title") or _tag(entry, "title"),
                url=f"https://www.youtube.com/watch?v={video_id}",
                source="youtube",
                meta=" · ".join(p for p in (author, published) if p),
                thumbnail=thumbnail_for(video_id),
            )
        )
    return items


async def _details(client: httpx.AsyncClient, video_id: str) -> tuple[str, str]:
    """(title, channel) for a video id. Blank on failure; never raises."""
    try:
        resp = await client.get(
            OEMBED_URL,
            params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
        )
        if resp.status_code != 200:
            return "", ""
        data = resp.json()
        return data.get("title", ""), data.get("author_name", "")
    except Exception:
        return "", ""


async def _search_videos_on_the_web(
    query: str, max_results: int, plan: dict | None = None
) -> list[ContentItem]:
    """No feed exists for a topic, so search the web and keep the videos.

    `query` is the user's own sentence. Asking for videos is the *search's*
    job, not something to graft onto what they wrote — so it goes through as
    `videos_only`, which adds a rule to the wrapper the search already has.

    What survives has no channel or thumbnail, so oembed fills those in.
    """
    from app.integrations.websearch.client import search_web  # lazy: import cycle

    # Over-fetch, because roughly half of what a web search returns is an
    # article *about* videos rather than a video — but capped, because
    # max_results arrives already tripled by the graph's own over-fetch.
    # Tripling it again asked a search for 27 pages to fill a block of three,
    # and binned 24 of them a second later.
    hits = await search_web(
        query,
        max_results=min(max_results * 3, MAX_WEB_PAGES),
        plan=plan,
        videos_only=True,
    )

    seen: set[str] = set()
    ids: list[str] = []
    for hit in hits:
        m = WATCH_RE.search(hit.url)
        if not m:
            continue
        video_id = m.group(1) or m.group(2)
        if video_id not in seen:
            seen.add(video_id)
            ids.append(video_id)
    ids = ids[:max_results]
    if not ids:
        return []

    async with httpx.AsyncClient(timeout=15) as client:
        details = await asyncio.gather(*(_details(client, v) for v in ids))

    return [
        ContentItem(
            id=video_id,
            title=title or "YouTube video",
            url=f"https://www.youtube.com/watch?v={video_id}",
            source="youtube",
            meta=author or None,
            thumbnail=thumbnail_for(video_id),
        )
        for video_id, (title, author) in zip(ids, details)
        if title or author  # a dead id returns nothing from oembed
    ]


async def search_videos(
    query: str,
    max_results: int = 3,
    latest: bool = False,
    channel: str = "",
    plan: dict | None = None,
) -> list[ContentItem]:
    """Videos for a block.

    `channel` is the supervisor's answer to "did the user name a channel?".
    Named means there is a feed to read; unnamed means there isn't, and the
    query is a topic — in which case `query` is the user's whole sentence, and
    `plan` carries the supervisor's other answers as context for the search.
    A channel that can't be resolved falls through to search rather than
    returning an empty block.
    """
    if channel:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                items = await _channel_uploads(client, channel, max_results)
            if items:
                return items
            logging.info("no feed for channel %r; searching instead", channel)
        except Exception:
            logging.warning("channel lookup failed for %r", channel, exc_info=True)

    return await _search_videos_on_the_web(query, max_results, plan)
