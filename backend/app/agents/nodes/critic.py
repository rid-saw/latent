"""Critic: self-reflection. Verifies fetched items fit the query; can trigger a refetch."""

from pydantic import BaseModel, Field

from app.agents.llm import structured_llm
from app.agents.state import BlockAgentState

PROMPT = """You are the quality gate for a content dashboard block.

The user asked for: {query}

A fetcher returned these items:
{items}

Judge whether they serve the request. Drop items that are off-topic, spammy, or \
clickbait (by index). If the overall set is weak and different search terms would \
likely do better, set approved=false and provide refined_search_terms."""


class Critique(BaseModel):
    approved: bool = Field(description="True if the (remaining) items serve the request well")
    drop_indexes: list[int] = Field(default_factory=list, description="Indexes of items to remove")
    refined_search_terms: str | None = Field(
        default=None, description="Better search terms, only if approved=false"
    )


async def critic_node(state: BlockAgentState) -> dict:
    items = state.get("items", [])
    if not items:
        # Nothing fetched (e.g. connector not authed) — nothing to critique.
        return {"approved": True}

    listing = "\n".join(
        f"[{i}] {it.title} — {it.meta or ''} — {(it.summary or '')[:150]}"
        for i, it in enumerate(items)
    )
    critique = await structured_llm(
        PROMPT.format(query=state["query"], items=listing), Critique
    )

    kept = [it for i, it in enumerate(items) if i not in set(critique.drop_indexes)]
    update: dict = {"approved": critique.approved, "items": kept}
    if not critique.approved and critique.refined_search_terms:
        update["search_terms"] = critique.refined_search_terms
    return update
