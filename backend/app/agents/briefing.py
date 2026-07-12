"""The briefing: ONE LLM call over all blocks' stored items.

Deliberately not a graph. A per-block summarize fan-out (LangGraph Send) ran
N+1 LLM calls per briefing; on request-metered backends (Claude subscription
window, free tiers) that's the wrong shape. The whole page is a few hundred
short lines at most, well within a single call.
"""

import re

from pydantic import BaseModel, Field

from app.agents.llm import structured_llm

SYNTH_PROMPT = """Write the user's briefing, a short morning paragraph for a \
personal dashboard. Below are their dashboard blocks, each with the content it \
is currently showing:

{blocks}

Rules: MAXIMUM 3 short sentences, under 55 words total. Lead with what matters \
most; cut anything skippable entirely rather than mentioning it. Conversational, \
information-dense, no bullets, no preamble, no sign-off. Never use em dashes \
(the — character); use commas or periods instead."""


class Briefing(BaseModel):
    briefing: str = Field(description="The single-paragraph briefing")


def _format_blocks(blocks: list[dict]) -> str:
    """[{title, query, items: [str, ...]}] -> one readable listing."""
    sections = []
    for b in blocks:
        lines = "\n".join(f"- {line}" for line in b["items"])
        sections.append(f'[{b["title"]}] (the user asked for: {b["query"]})\n{lines}')
    return "\n\n".join(sections)


def _strip_em_dashes(text: str) -> str:
    """Prompt bans aren't reliable; enforce deterministically."""
    text = re.sub(r"\s*[—–]\s*", ", ", text)
    return re.sub(r",\s*,", ",", text)


async def run_briefing(blocks: list[dict]) -> str:
    result = await structured_llm(
        SYNTH_PROMPT.format(blocks=_format_blocks(blocks)), Briefing
    )
    return _strip_em_dashes(result.briefing)
