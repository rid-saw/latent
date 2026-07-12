"""The Briefing: parallel per-block summarizers fan out via Send, then a
synthesizer writes one short briefing across everything.

  START -(Send per block)-> summarize_block (xN, parallel) -> synthesize -> END
"""

import operator
import re
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

In ONE punchy sentence, tell the user the single thing worth their attention here \
(or that it's all noise). Never use em dashes; use commas or periods instead."""

SYNTH_PROMPT = """Write the user's briefing, a short morning paragraph for a \
personal dashboard, from these per-block summaries:

{summaries}

Rules: MAXIMUM 3 short sentences, under 55 words total. Lead with what matters \
most; cut anything skippable entirely rather than mentioning it. Conversational, \
information-dense, no bullets, no preamble, no sign-off. Never use em dashes \
(the — character); use commas or periods instead."""


class BriefingState(TypedDict):
    blocks: list[dict]  # [{title, query, items: [str, ...]}]
    summaries: Annotated[list[str], operator.add]
    briefing: str


class BlockSummary(BaseModel):
    summary: str = Field(description="1-2 sentences on what's worth attention")


class Briefing(BaseModel):
    briefing: str = Field(description="The single-paragraph briefing")


def _dispatch(state: BriefingState) -> list[Send]:
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


async def synthesize(state: BriefingState) -> dict:
    result = await structured_llm(
        SYNTH_PROMPT.format(summaries="\n".join(state["summaries"])), Briefing
    )
    return {"briefing": result.briefing}


@lru_cache
def get_briefing_graph():
    g = StateGraph(BriefingState)
    g.add_node("summarize_block", summarize_block)
    g.add_node("synthesize", synthesize)
    g.add_conditional_edges(START, _dispatch, ["summarize_block"])
    g.add_edge("summarize_block", "synthesize")
    g.add_edge("synthesize", END)
    return g.compile()


def _strip_em_dashes(text: str) -> str:
    """Prompt bans aren't reliable; enforce deterministically."""
    text = re.sub(r"\s*[—–]\s*", ", ", text)
    return re.sub(r",\s*,", ",", text)


async def run_briefing(blocks: list[dict]) -> str:
    state = await get_briefing_graph().ainvoke({"blocks": blocks, "summaries": []})
    return _strip_em_dashes(state["briefing"])
