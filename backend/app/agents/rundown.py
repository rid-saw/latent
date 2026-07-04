"""The Rundown: parallel per-block summarizers fan out via Send, then a
synthesizer writes one short briefing across everything.

  START -(Send per block)-> summarize_block (xN, parallel) -> synthesize -> END
"""

import operator
from functools import lru_cache
from typing import Annotated, TypedDict

from langgraph.constants import Send
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.llm import structured_llm

SUMMARIZE_PROMPT = """You summarize one content block of a personal dashboard.

Block: "{title}" (the user asked for: {query})
Fresh items:
{items}

In 1-2 punchy sentences, tell the user what's actually worth their attention here. \
Name the standout item if there is one; say so plainly if it's all noise. \
Never use em dashes; use commas, periods, or semicolons instead."""

SYNTH_PROMPT = """Write "The Rundown" — a short morning-briefing paragraph for a \
personal dashboard, from these per-block summaries:

{summaries}

Rules: one tight paragraph, conversational but information-dense, no bullet points, \
no preamble, no sign-off. Lead with whatever matters most. Never use em dashes \
(the — character); use commas, periods, or semicolons instead."""


class RundownState(TypedDict):
    blocks: list[dict]  # [{title, query, items: [str, ...]}]
    summaries: Annotated[list[str], operator.add]
    briefing: str


class BlockSummary(BaseModel):
    summary: str = Field(description="1-2 sentences on what's worth attention")


class Briefing(BaseModel):
    briefing: str = Field(description="The single-paragraph rundown")


def _dispatch(state: RundownState) -> list[Send]:
    return [Send("summarize_block", {"block": b}) for b in state["blocks"]]


async def summarize_block(payload: dict) -> dict:
    block = payload["block"]
    result = await structured_llm(
        SUMMARIZE_PROMPT.format(
            title=block["title"],
            query=block["query"],
            items="\n".join(f"- {line}" for line in block["items"]),
        ),
        BlockSummary,
    )
    return {"summaries": [f"[{block['title']}] {result.summary}"]}


async def synthesize(state: RundownState) -> dict:
    result = await structured_llm(
        SYNTH_PROMPT.format(summaries="\n".join(state["summaries"])), Briefing
    )
    return {"briefing": result.briefing}


@lru_cache
def get_rundown_graph():
    g = StateGraph(RundownState)
    g.add_node("summarize_block", summarize_block)
    g.add_node("synthesize", synthesize)
    g.add_conditional_edges(START, _dispatch, ["summarize_block"])
    g.add_edge("summarize_block", "synthesize")
    g.add_edge("synthesize", END)
    return g.compile()


async def run_rundown(blocks: list[dict]) -> str:
    state = await get_rundown_graph().ainvoke({"blocks": blocks, "summaries": []})
    return state["briefing"]
