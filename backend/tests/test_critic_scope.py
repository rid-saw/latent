"""The critic runs where a second opinion can help, and nowhere else.

Judging results is worth an LLM call when the fetch was a blunt string match
against a large noisy index — Google News, Seek, OpenAlex, a Gmail topic
search. It is worth nothing when the fetch was exact (a channel's own upload
feed, an ESPN league endpoint) or was already made by a model against the
user's own words (web search, and the YouTube topic search that runs on top of
it).

Measured before it was changed: across four blocks the critic altered nothing
the user could see, while costing an LLM call and a three-times over-fetch
every time. Those spares exist only so it has something to prune, so they are
gated on the same set.
"""

import pytest

from app.agents import graph
from app.agents.nodes.critic import JUDGED_SOURCES, critic_node
from app.models.schemas import ContentItem


def _items(n: int, source: str = "news") -> list[ContentItem]:
    return [
        ContentItem(id=str(i), title=f"item {i}", url=f"https://e.com/{i}", source=source)
        for i in range(n)
    ]


@pytest.fixture
def never_called(monkeypatch):
    def explode(*a, **k):
        raise AssertionError("an LLM call was spent on an unjudged source")

    monkeypatch.setattr("app.agents.nodes.critic.structured_llm", explode)


@pytest.mark.parametrize("source", ["youtube", "web", "sports", "site"])
async def test_unjudged_sources_cost_no_llm_call(source, never_called):
    out = await critic_node(
        {"source": source, "items": _items(9, source), "query": "anything", "max_items": 3}
    )
    assert out == {"approved": True}


@pytest.mark.parametrize("source", ["news", "jobs", "papers", "gmail"])
async def test_judged_sources_are_still_judged(source, monkeypatch):
    from app.agents.nodes.critic import Critique

    async def critique(*a, **k):
        return Critique(approved=True, drop_indexes=[1], refined_search_terms=None)

    monkeypatch.setattr("app.agents.nodes.critic.structured_llm", critique)

    out = await critic_node(
        {"source": source, "items": _items(9, source), "query": "anything", "max_items": 3}
    )
    assert [i.id for i in out["items"]] == ["0", "2", "3", "4", "5", "6", "7", "8"]


@pytest.mark.parametrize(
    "source,max_items,expected",
    [
        # Judged: over-fetch so the critic has spares to prune.
        ("news", 3, 9),
        ("gmail", 5, 15),
        ("papers", 10, 15),  # MAX_FETCH caps it
        # Unjudged: nothing is going to prune, so the spares were pure waste.
        ("web", 3, 3),
        ("youtube", 3, 3),
        ("sports", 5, 5),
    ],
)
async def test_only_judged_sources_over_fetch(source, max_items, expected, monkeypatch):
    asked = {}

    async def spy(terms, max_results=3, **kw):
        asked["n"] = max_results
        return []

    for name in ("search_videos", "search_web", "search_jobs"):
        monkeypatch.setattr(graph, name, spy)
    monkeypatch.setattr(graph, "_CONNECTORS", dict.fromkeys(graph._CONNECTORS, spy))

    await graph.fetch_node({"source": source, "search_terms": "x", "max_items": max_items})
    assert asked["n"] == expected


def test_the_two_lists_together_cover_every_source():
    """A new connector must be a deliberate choice, not a default."""
    from app.models.schemas import SourceKind
    from typing import get_args

    unjudged = {"youtube", "web", "sports", "site"}
    assert JUDGED_SOURCES | unjudged == set(get_args(SourceKind))
    assert not JUDGED_SOURCES & unjudged
