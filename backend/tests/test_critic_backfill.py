"""Critic pruning must never leave a block with less than the user asked for.

Regression: asked for 3 emails "from monash uni", the connector returned 9
genuinely from Monash, and the critic dropped 7 of them on topical grounds —
an event invite and a staff notice were judged uninteresting. The block showed
one email. The user asked about origin, not interest, so nothing there was
off-topic; and even when a drop is fair, an item ranked lower beats a gap.

Gmail is one of the sources the critic still judges, so these guards are
live — see JUDGED_SOURCES.
"""

import pytest

from app.agents.nodes import critic
from app.models.schemas import ContentItem


def items(n: int) -> list[ContentItem]:
    """n items, newest first — index order is recency order."""
    return [
        ContentItem(id=str(i), title=f"email {i}", url="https://x", source="gmail")
        for i in range(n)
    ]


@pytest.fixture
def verdict(monkeypatch):
    """Stub the LLM so the test asserts on our handling, not the model's mood."""

    def set_verdict(drop, approved=True, refined=None):
        async def fake(prompt, schema):
            return critic.Critique(
                approved=approved, drop_indexes=drop, refined_search_terms=refined
            )

        monkeypatch.setattr(critic, "structured_llm", fake)

    return set_verdict


async def test_backfills_to_max_items(verdict):
    verdict(drop=[1, 2, 3, 4, 5, 6, 7, 8])  # keeps only index 0
    out = await critic.critic_node({"source": "gmail", "query": "q", "items": items(9), "max_items": 3})
    assert [i.id for i in out["items"]] == ["0", "1", "2"], "newest survivors fill the gap"


async def test_backfill_preserves_recency_order(verdict):
    verdict(drop=[0, 1])  # the two newest get dropped
    out = await critic.critic_node({"source": "gmail", "query": "q", "items": items(4), "max_items": 3})
    assert [i.id for i in out["items"]] == ["0", "2", "3"], "restored items stay in place"


async def test_no_backfill_when_enough_survive(verdict):
    verdict(drop=[3, 4])
    out = await critic.critic_node({"source": "gmail", "query": "q", "items": items(5), "max_items": 3})
    assert [i.id for i in out["items"]] == ["0", "1", "2"], "real drops still apply"


async def test_fewer_results_than_asked_for_is_left_alone(verdict):
    """Backfill can only give back what was fetched — it never invents items."""
    verdict(drop=[1])
    out = await critic.critic_node({"source": "gmail", "query": "q", "items": items(2), "max_items": 5})
    assert len(out["items"]) == 2


async def test_out_of_range_drop_indexes_are_ignored(verdict):
    verdict(drop=[0, 99, -1])
    out = await critic.critic_node({"source": "gmail", "query": "q", "items": items(3), "max_items": 3})
    assert len(out["items"]) == 3
