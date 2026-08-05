"""The web connector must degrade to news rather than show a blank card.

`web` is the catch-all source, so it runs on backends whose CLI cannot search
at all. Whenever the search can't answer, the block falls back to Google News
RSS: worse than a real search, but never worse than before search existed.

No network and no LLM here; the CLI call is stubbed so the tests assert on our
handling rather than on what a live search happens to return today.
"""

import pytest

from app.agents import llm
from app.integrations.websearch import client as websearch
from app.models.schemas import ContentItem


def news_item(title: str = "from news") -> ContentItem:
    return ContentItem(id="n1", title=title, url="https://news.example", source="news")


@pytest.fixture
def news_fallback(monkeypatch):
    """Stub the news connector so a fallback is obvious in assertions."""

    async def fake_news(query, max_results=3):
        return [news_item()]

    monkeypatch.setattr(websearch, "search_news", fake_news)


def stub_search(monkeypatch, hits=None, raises=None):
    """Stub the CLI call that would normally run the search."""

    async def fake(prompt, schema, web=False):
        assert web is True, "the web connector must ask for search"
        if raises:
            raise raises
        return websearch._Hits(results=hits or [])

    monkeypatch.setattr(llm, "structured_llm", fake)


def test_site_strips_www_and_path():
    assert websearch._site("https://www.example.com/a/b?c=1") == "example.com"
    assert websearch._site("https://docs.python.org/3/") == "docs.python.org"


async def test_search_results_become_items(monkeypatch, news_fallback):
    stub_search(monkeypatch, hits=[
        websearch._Hit(title="ANZ housing outlook", url="https://www.anz.com.au/x",
                       summary="Forecast.", published="April 2026"),
    ])
    items = await websearch.search_web("australian housing market")
    assert [i.title for i in items] == ["ANZ housing outlook"]
    assert items[0].source == "web"
    assert items[0].meta == "anz.com.au · April 2026"


async def test_backend_without_search_falls_back_to_news(monkeypatch, news_fallback):
    """A CLI that can't search must not answer from memory with invented URLs."""
    stub_search(monkeypatch, raises=llm.WebSearchUnavailable("codex cannot search"))
    items = await websearch.search_web("best mechanical keyboards")
    assert [i.source for i in items] == ["news"]


async def test_search_failure_falls_back_to_news(monkeypatch, news_fallback):
    stub_search(monkeypatch, raises=RuntimeError("claude exited 1"))
    items = await websearch.search_web("anything")
    assert [i.source for i in items] == ["news"]


async def test_empty_search_falls_back_to_news(monkeypatch, news_fallback):
    stub_search(monkeypatch, hits=[])
    items = await websearch.search_web("query with no good pages")
    assert [i.source for i in items] == ["news"]


async def test_non_http_urls_are_dropped(monkeypatch, news_fallback):
    """A hallucinated bare title must never reach the card as a link."""
    stub_search(monkeypatch, hits=[
        websearch._Hit(title="real", url="https://example.com/a"),
        websearch._Hit(title="not a link", url="example.com/b"),
    ])
    items = await websearch.search_web("q")
    assert [i.title for i in items] == ["real"]


async def test_respects_max_results(monkeypatch, news_fallback):
    stub_search(monkeypatch, hits=[
        websearch._Hit(title=f"hit {n}", url=f"https://example.com/{n}") for n in range(9)
    ])
    items = await websearch.search_web("q", max_results=3)
    assert len(items) == 3
