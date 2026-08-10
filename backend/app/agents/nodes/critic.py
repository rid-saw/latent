"""Critic: self-reflection. Verifies fetched items fit the query; can trigger a refetch."""

from pydantic import BaseModel, Field

from app.agents.llm import structured_llm
from app.agents.state import BlockAgentState

PROMPT = """You are the quality gate for a content dashboard block.

The user asked for: {query}

A fetcher returned these items:
{items}

Judge whether they serve the request. Drop items that are off-topic, spammy, or \
clickbait (by index).

IMPORTANT exception — origin requests. If the request names where content \
should come FROM (a channel, publication, person, organisation, or email \
sender) — "emails from monash uni", "latest from Fireship" — then origin and \
recency are the ONLY criteria. Keep every item genuinely from that source no \
matter how varied or mundane its subject. Newsletters, event invites, admin \
notices and reminders all belong. Judging those on interest answers a question \
the user did not ask, and leaves the block empty.

If the overall set is weak and different search terms would likely do better, \
set approved=false and provide refined_search_terms.

refined_search_terms go straight to a keyword search API, not to a person. \
Every word must literally appear in a matching result, so use the fewest, most \
distinctive words — "monash", not "Monash University news and announcements". \
A descriptive phrase matches nothing."""


class Critique(BaseModel):
    approved: bool = Field(description="True if the (remaining) items serve the request well")
    drop_indexes: list[int] = Field(default_factory=list, description="Indexes of items to remove")
    refined_search_terms: str | None = Field(
        default=None,
        description="A few distinctive keywords for a search API (e.g. 'monash'), "
        "never a descriptive phrase. Only if approved=false",
    )


async def critic_node(state: BlockAgentState) -> dict:
    items = state.get("items", [])
    if not items:
        # Nothing fetched (e.g. connector not authed) — nothing to critique.
        return {"approved": True}
    if state.get("regressed"):
        # The refinement was already rejected as worse; re-critiquing the
        # restored items would only spend another request to reach the same
        # verdict it gave last round.
        return {"approved": True}

    listing = "\n".join(
        f"[{i}] {it.title} — {it.meta or ''} — {(it.summary or '')[:150]}"
        for i, it in enumerate(items)
    )
    critique = await structured_llm(
        PROMPT.format(query=state["query"], items=listing), Critique
    )

    dropped = {i for i in critique.drop_indexes if 0 <= i < len(items)}
    keep = [i for i in range(len(items)) if i not in dropped]

    # Pruning must never starve the block. The user asked for max_items; an
    # item the critic ranked lower still beats an empty slot, and the graph
    # over-fetches precisely so there's slack to give back. Top up with the
    # newest of the dropped items, keeping the original (recency) order.
    want = state.get("max_items", 3)
    if len(keep) < want:
        keep = sorted(keep + sorted(dropped)[: want - len(keep)])

    kept = [items[i] for i in keep]
    update: dict = {"approved": critique.approved, "items": kept}
    # Dropping off-topic items is worth doing for every source. Rewriting the
    # search is not: a verbatim source holds the user's own sentence here, it
    # will not be refetched, and this string is persisted and reused by every
    # later refresh — so overwriting it with keywords would quietly undo the
    # whole point of sending the request intact.
    if not critique.approved and critique.refined_search_terms and not state.get("verbatim"):
        update["search_terms"] = critique.refined_search_terms
    return update
