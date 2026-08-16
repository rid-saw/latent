"""The web connector answers, or says it couldn't. It never substitutes.

`web` is the catch-all source and the only one that can hold an answer rather
than a list of pages. Google News used to stand in whenever the search failed,
from when a web block was a list of links and headlines were a fair
substitute. They are not a substitute for an answer: "how do I make cold brew"
served with news articles about coffee is not a worse answer, it is a
different thing wearing the shape of one. An empty block is the honest report.

No network and no LLM here; the CLI call is stubbed so the tests assert on our
handling rather than on what a live search happens to return today.
"""

import pytest

from app.agents import llm
from app.integrations.websearch import client as websearch


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


async def test_search_results_become_items(monkeypatch):
    stub_search(monkeypatch, hits=[
        websearch._Hit(title="ANZ housing outlook", url="https://www.anz.com.au/x",
                       summary="Forecast.", published="April 2026"),
    ])
    items = await websearch.search_web("australian housing market")
    assert [i.title for i in items] == ["ANZ housing outlook"]
    assert items[0].source == "web"
    assert items[0].meta == "anz.com.au · April 2026"


async def test_a_backend_that_cannot_search_returns_nothing(monkeypatch):
    """Codex has no web search. Answering from memory would mean invented URLs,
    and answering with headlines would mean answering a different question."""
    stub_search(monkeypatch, raises=llm.WebSearchUnavailable("codex cannot search"))
    assert await websearch.search_web("best mechanical keyboards") == []


async def test_a_failed_search_returns_nothing(monkeypatch):
    stub_search(monkeypatch, raises=RuntimeError("claude exited 1"))
    assert await websearch.search_web("anything") == []


async def test_an_empty_search_returns_nothing(monkeypatch):
    stub_search(monkeypatch, hits=[])
    assert await websearch.search_web("query with no good pages") == []


@pytest.mark.parametrize("fmt", ["links", "table", "steps", "stat", "text"])
async def test_no_format_gets_a_substitute(monkeypatch, fmt):
    """Whatever shape was asked for, an empty answer stays empty."""
    stub_search(monkeypatch, hits=[])
    assert await websearch.search_web("q", fmt=fmt, fields=["price"]) == []


async def test_non_http_urls_are_dropped(monkeypatch):
    """A hallucinated bare title must never reach the card as a link."""
    stub_search(monkeypatch, hits=[
        websearch._Hit(title="real", url="https://example.com/a"),
        websearch._Hit(title="not a link", url="example.com/b"),
    ])
    items = await websearch.search_web("q")
    assert [i.title for i in items] == ["real"]


async def test_respects_max_results(monkeypatch):
    stub_search(monkeypatch, hits=[
        websearch._Hit(title=f"hit {n}", url=f"https://example.com/{n}") for n in range(9)
    ])
    items = await websearch.search_web("q", max_results=3)
    assert len(items) == 3
