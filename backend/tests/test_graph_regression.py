"""A refinement that finds less than the round before it must be rejected.

Regression: the critic replaced working search terms ("monash", 3 emails) with
a descriptive phrase ("Monash University news and announcements", 0 emails).
The graph accepted the empty refetch as final and persisted those terms on the
block, so every later refresh searched with them and came back empty — the
block was broken permanently, not just for one fetch.
"""

import pytest

from app.agents import graph
from app.models.schemas import ContentItem


def item(n: int) -> ContentItem:
    return ContentItem(id=str(n), title=f"email {n}", url="https://x", source="gmail")


@pytest.fixture
def fake_gmail(monkeypatch):
    """Connector whose result depends on the terms it's given."""
    by_terms = {"monash": [item(1), item(2), item(3)], "a long descriptive phrase": []}

    async def search(terms, max_results=3):
        return by_terms.get(terms, [])

    monkeypatch.setitem(graph._CONNECTORS, "gmail", search)
    return by_terms


async def test_first_round_keeps_what_it_found(fake_gmail):
    out = await graph.fetch_node(
        {"source": "gmail", "search_terms": "monash", "iterations": 0}
    )
    assert len(out["items"]) == 3
    assert out["prev_terms"] == "monash"
    assert not out.get("regressed")


async def test_worse_refinement_is_reverted(fake_gmail):
    """Round 2 finds nothing -> keep round 1's items AND its search terms."""
    out = await graph.fetch_node(
        {
            "source": "gmail",
            "search_terms": "a long descriptive phrase",  # the critic's rewrite
            "prev_terms": "monash",
            "items": [item(1), item(2), item(3)],
            "iterations": 1,
        }
    )
    assert len(out["items"]) == 3, "should keep the better round's items"
    assert out["search_terms"] == "monash", "must persist terms that actually work"
    assert out["regressed"] is True


async def test_better_refinement_is_kept(fake_gmail):
    """The guard must not block genuine improvements."""
    fake_gmail["broader"] = [item(1), item(2), item(3), item(4)]
    out = await graph.fetch_node(
        {
            "source": "gmail",
            "search_terms": "broader",
            "prev_terms": "monash",
            "items": [item(1)],
            "iterations": 1,
        }
    )
    assert len(out["items"]) == 4
    assert out["prev_terms"] == "broader"
    assert not out.get("regressed")


async def test_critic_skips_after_a_regression():
    """No second opinion needed — and no second request spent."""
    verdict = await graph.critic_node(
        {"query": "q", "items": [item(1)], "regressed": True}
    )
    assert verdict == {"approved": True}
