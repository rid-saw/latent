"""Critic: self-reflection. Verifies fetched items fit the query; can trigger a refetch.

It runs on some sources and not others. Judging results is worth an LLM call
where the fetch is a blunt string match against a large noisy index, and worth
nothing where the fetch is exact or was already made by a model — see
JUDGED_SOURCES.
"""

from pydantic import BaseModel, Field

from app.agents.llm import structured_llm
from app.agents.state import BlockAgentState

# Sources whose results are worth a second opinion.
#
#   news    Google News matches strings against everything ever published;
#           press releases and tangential articles come back routinely
#   jobs    Seek's keyword match returns senior roles and sales jobs for a
#           graduate engineering search
#   papers  OpenAlex can surface papers where the terms appear incidentally,
#           and its arXiv fallback sorts by date rather than relevance, so an
#           unrelated recent paper containing all the words ranks first
#   gmail   a topic search can match the wrong thread
#
# Deliberately absent, because a second opinion cannot help:
#
#   youtube a named channel's upload feed is that channel by definition, and a
#           topic search is already filtered to real videos in code
#   web     the CLI chose these pages against the user's own request; a second
#           model re-judging the first model's picks mostly costs 20 seconds
#   sports  the ESPN endpoint returns that league's news and nothing else
#   site    a pinned URL never reaches the agent at all
JUDGED_SOURCES = {"news", "jobs", "papers", "gmail"}

PROMPT = """You are the quality gate for a content dashboard block.

The user asked for: {query}

A fetcher returned these items:
{items}

Judge whether they serve the request. Drop items that are off-topic, spammy, or \
clickbait (by index).

IMPORTANT exception — origin requests. If the request names where content \
should come FROM (a publication, person, organisation, or email sender) — \
"emails from monash uni", "anything from Nature" — then origin and recency \
are the ONLY criteria. Keep every item genuinely from that source no matter \
how varied or mundane its subject. Newsletters, event invites, admin notices \
and reminders all belong. Judging those on interest answers a question the \
user did not ask, and leaves the block empty.

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
    if state.get("source") not in JUDGED_SOURCES:
        return {"approved": True}
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
    if not critique.approved and critique.refined_search_terms:
        update["search_terms"] = critique.refined_search_terms
    return update
