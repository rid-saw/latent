"""YouTube without an account: which path a request takes, and what it needs.

The Data API needed `youtube.readonly` — permission to read the user's
account — and the connector never read it. It searched public videos, which
needs no permission at all. Because that scope was requested alongside Gmail,
a user granted read access to their inbox in exchange for video search, and
got no personalisation for it.

Two public surfaces replace it. A named channel has an upload feed to read; a
topic does not, so it goes through web search. The supervisor decides which by
answering "did the user name a channel?", the same way it already answers
"did the user name a city?" for jobs.

No network here: the feed and the search are stubbed, so these test the
routing and parsing rather than what YouTube happens to be serving today.
"""

import httpx
import pytest

from app.integrations.youtube import client as yt
from app.models.schemas import ContentItem

FEED = """<?xml version="1.0"?>
<feed>
  <title>Fireship</title>
  <entry>
    <yt:videoId>abc12345678</yt:videoId>
    <media:title>Rust in 100 Seconds</media:title>
    <name>Fireship</name>
    <published>2026-08-05T10:00:00+00:00</published>
  </entry>
  <entry>
    <yt:videoId>def12345678</yt:videoId>
    <media:title>TypeScript &amp; you</media:title>
    <name>Fireship</name>
    <published>2026-07-29T10:00:00+00:00</published>
  </entry>
</feed>"""

CHANNEL_PAGE = """<html><head>
  <meta property="og:url" content="https://www.youtube.com/@fireship">
  <script>{"channelId":"UCwrongChannel00"}</script>
  <link rel="canonical" href="https://www.youtube.com/channel/UCsBjURrPoezykLs9EqgamOA">
</head></html>"""


def fake_transport(routes: dict[str, httpx.Response]):
    """Serve canned responses by URL fragment; 404 for anything unexpected."""

    def handler(request: httpx.Request) -> httpx.Response:
        for fragment, response in routes.items():
            if fragment in str(request.url):
                return response
        return httpx.Response(404)

    return httpx.MockTransport(handler)


@pytest.fixture
def serve(monkeypatch):
    def _serve(routes):
        transport = fake_transport(routes)
        original = httpx.AsyncClient

        def patched(*a, **kw):
            kw["transport"] = transport
            return original(*a, **kw)

        monkeypatch.setattr(yt.httpx, "AsyncClient", patched)

    return _serve


def test_thumbnail_comes_from_the_id_alone():
    """No lookup needed: the path is fixed, so an id is enough."""
    assert yt.thumbnail_for("abc12345678") == "https://i.ytimg.com/vi/abc12345678/hqdefault.jpg"


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.youtube.com/watch?v=abc12345678", "abc12345678"),
        ("https://youtu.be/abc12345678", "abc12345678"),
        ("https://www.youtube.com/watch?v=abc12345678&t=30s", "abc12345678"),
        ("https://medium.com/best-youtube-channels-for-rust", None),
        ("https://www.youtube.com/@fireship", None),
    ],
)
def test_only_real_video_links_are_kept(url, expected):
    """Search returns articles about videos too; those aren't videos."""
    m = yt.WATCH_RE.search(url)
    assert (m.group(1) or m.group(2) if m else None) == expected


async def test_named_channel_reads_its_upload_feed(serve):
    serve({"youtube.com/@": httpx.Response(200, text=CHANNEL_PAGE),
           "feeds/videos.xml": httpx.Response(200, text=FEED)})

    items = await yt.search_videos("fireship", max_results=2, channel="Fireship")
    assert [i.title for i in items] == ["Rust in 100 Seconds", "TypeScript & you"]
    assert items[0].meta == "Fireship · 2026-08-05"
    assert items[0].thumbnail == "https://i.ytimg.com/vi/abc12345678/hqdefault.jpg"
    assert items[0].url == "https://www.youtube.com/watch?v=abc12345678"


async def test_channel_id_comes_from_the_canonical_link(serve):
    """The page names several channels; only the canonical one is itself.

    Reading the first "channelId" in the HTML resolves @fireship to Beyond
    Fireship, which is a different channel with different videos.
    """
    serve({"youtube.com/@": httpx.Response(200, text=CHANNEL_PAGE)})
    async with httpx.AsyncClient() as c:
        assert await yt._channel_id(c, "@fireship") == "UCsBjURrPoezykLs9EqgamOA"


async def test_an_unresolvable_channel_searches_instead(serve, monkeypatch):
    """A typo must not produce an empty block."""
    serve({"youtube.com/@": httpx.Response(404)})

    called = {}

    async def fake_search(query, max_results=3, **kw):
        called["query"] = query
        called.update(kw)
        return [ContentItem(id="x", title="found anyway",
                            url="https://www.youtube.com/watch?v=abc12345678",
                            source="youtube")]

    monkeypatch.setattr("app.integrations.websearch.client.search_web", fake_search)
    monkeypatch.setattr(yt, "_details", lambda c, v: _ok())

    items = await yt.search_videos("rust", max_results=2, channel="NoSuchChannel")
    assert len(items) == 1, "fell through to search rather than returning nothing"
    assert "rust" in called["query"]


async def _ok():
    return ("found anyway", "Some Channel")


async def test_topic_search_keeps_videos_and_drops_articles(monkeypatch):
    async def fake_search(query, max_results=3, **kw):
        return [
            ContentItem(id="1", title="Best YouTube channels for Rust",
                        url="https://medium.com/best-rust-channels", source="web"),
            ContentItem(id="2", title="Rust Crash Course",
                        url="https://www.youtube.com/watch?v=abc12345678", source="web"),
            ContentItem(id="3", title="dupe",
                        url="https://youtu.be/abc12345678", source="web"),
        ]

    monkeypatch.setattr("app.integrations.websearch.client.search_web", fake_search)
    monkeypatch.setattr(yt, "_details", lambda c, v: _ok())

    items = await yt.search_videos("rust programming", max_results=3)
    assert len(items) == 1, "the article is dropped and the duplicate collapsed"
    assert items[0].meta == "Some Channel", "channel filled in from oembed"
    assert items[0].thumbnail.endswith("abc12345678/hqdefault.jpg")


async def test_a_searched_video_shows_its_upload_date(monkeypatch):
    """oEmbed has no date field, so the search's is the only one there is.

    It used to be dropped on the way through, leaving the card showing a
    channel name and nothing else — a 2023 video looked exactly like last
    week's, which is how a block of ancient videos went unnoticed.
    """
    async def fake_search(query, max_results=3, **kw):
        return [
            ContentItem(id="1", title="a video",
                        url="https://www.youtube.com/watch?v=abc12345678",
                        source="web", meta="youtube.com · 2026-07-15"),
            ContentItem(id="2", title="undated",
                        url="https://www.youtube.com/watch?v=def12345678",
                        source="web", meta="youtube.com"),
        ]

    monkeypatch.setattr("app.integrations.websearch.client.search_web", fake_search)
    monkeypatch.setattr(yt, "_details", lambda c, v: _ok())

    items = await yt.search_videos("rust", max_results=2)
    assert items[0].meta == "Some Channel · 2026-07-15"
    # The same shape the channel feed produces, so a video looks the same
    # whichever path found it — and a missing date leaves no dangling divider.
    assert items[1].meta == "Some Channel"
