"""Supervisor: interprets the block query and routes to a source (delegation)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.agents.llm import structured_llm
from app.agents.state import BlockAgentState

PROMPT = """You route content-dashboard block requests. The user describes what they \
want to keep up with; decide which source serves it best and produce focused search \
terms for that source's API.

Sources: youtube (videos), papers (research across arXiv/Nature/journals via \
Semantic Scholar; include publication names in search terms if the user names one), \
gmail (the user's own inbox), news (Google News, any topic), sports (ESPN leagues: \
NBA/NFL/MLB/NHL/soccer/F1/golf), web (generic — resolved via news search).

User request: {query}"""


class Plan(BaseModel):
    source: Literal["youtube", "gmail", "papers", "news", "sports", "web"]
    search_terms: str = Field(description="Concise search terms for the source API")
    title: str = Field(description="Short block title, max 5 words")
    max_items: int = Field(
        ge=1,
        le=10,
        description="How many items to show: the number the user asked for if they "
        "named one, else 3",
    )
    wants_latest: bool = Field(
        description="True if the user wants the newest/most recent items "
        "(e.g. 'latest', 'newest', 'new videos from X') rather than the most relevant"
    )


async def supervisor_node(state: BlockAgentState) -> dict:
    plan = await structured_llm(PROMPT.format(query=state["query"]), Plan)
    return {
        "source": plan.source,
        "search_terms": plan.search_terms,
        "title": plan.title,
        "max_items": plan.max_items,
        "wants_latest": plan.wants_latest,
    }
