"""Supervisor: interprets the block query and routes to a source (delegation)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.agents.llm import structured_llm
from app.agents.state import BlockAgentState

PROMPT = """You route content-dashboard block requests. The user describes what they \
want to keep up with; decide which source serves it best and produce focused search \
terms for that source's API.

Sources: youtube (videos), papers (arXiv research), gmail (the user's own inbox), \
news, sports, web.
Only youtube, papers and gmail have live connectors; pick the closest match anyway.

User request: {query}"""


class Plan(BaseModel):
    source: Literal["youtube", "gmail", "papers", "news", "sports", "web"]
    search_terms: str = Field(description="Concise search terms for the source API")
    title: str = Field(description="Short block title, max 5 words")


async def supervisor_node(state: BlockAgentState) -> dict:
    plan = await structured_llm(PROMPT.format(query=state["query"]), Plan)
    return {"source": plan.source, "search_terms": plan.search_terms, "title": plan.title}
