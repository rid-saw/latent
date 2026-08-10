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
gmail (the user's own inbox), news (Google News: current events and headlines, \
what just happened), sports (ESPN leagues: NBA/NFL/MLB/NHL/soccer/F1/golf), jobs \
(job listings via Seek, AU/NZ; search_terms = role keywords only, put any \
city/region in location), web (a real web search, for everything else).

Choosing between news and web is the call you will get wrong most often. Pick \
news only when the user wants recent events reported as news: "NBA trade news", \
"election results", "what happened at the budget". Pick web for everything \
else, including topics that merely sound newsworthy: how something works, \
reviews and comparisons, background on a subject, documentation, ongoing \
conditions. "australian housing market" is web, not news, because the user \
wants to understand the market rather than read this week's headlines about \
it. When both could fit, prefer web: it can return news articles, but news \
cannot return anything else.

For gmail: search_terms is a Gmail search query, not a description of one. \
Gmail requires EVERY word to appear in the message, so use the fewest, most \
distinctive words. Always drop words describing the request rather than its \
content ("emails", "my", "inbox", "recent") and casual abbreviations that \
won't appear verbatim ("uni").

Then pick ONE form:
- Mail FROM a person or organisation -> Gmail's sender operator, using their \
real domain: "monash uni emails" and "emails from monash uni" both -> \
"from:monash.edu". Never a bare name here — that also matches job alerts and \
newsletters merely mentioning them, which is not what "from" means.
- Mail ABOUT a topic -> plain keywords: "emails about my enrolment" -> \
"enrolment".

User request: {query}"""


class Plan(BaseModel):
    source: Literal["youtube", "gmail", "papers", "news", "sports", "jobs", "web"]
    search_terms: str = Field(description="Concise search terms for the source API")
    location: str = Field(
        default="",
        description="For jobs only: city/region if the user named one, else empty",
    )
    channel: str = Field(
        default="",
        description="For youtube only: the channel or creator if the user named "
        "one ('latest Fireship videos' -> 'Fireship'), else empty. A named "
        "channel is read from its upload feed; without one the request is a "
        "topic and gets searched.",
    )
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


def searches_with_the_users_own_words(source: str, channel: str) -> bool:
    """Which sources read the request itself rather than extracted keywords.

    Every other connector is a keyword index — Gmail needs every word to match,
    arXiv ANDs them, Seek wants role words only — so a sentence returns nothing
    and the terms are doing real work. These two hand the string to a language
    model, which can act on detail the others would choke on. Compressing for
    them throws away the only part they could have used.

    Decided here, in code, rather than asked of the model: told to "keep the
    request verbatim" it complies unevenly, passing one prompt through intact
    and squeezing the next one down to four words.
    """
    return source == "web" or (source == "youtube" and not channel)


async def supervisor_node(state: BlockAgentState) -> dict:
    plan = await structured_llm(PROMPT.format(query=state["query"]), Plan)
    verbatim = searches_with_the_users_own_words(plan.source, plan.channel)
    return {
        "source": plan.source,
        # For a verbatim source this is the request itself. It is also what
        # gets persisted on the block and reused by every later refresh, so
        # storing the whole sentence is what keeps refreshes as good as the
        # first fetch.
        "search_terms": state["query"] if verbatim else plan.search_terms,
        "verbatim": verbatim,
        "location": plan.location,
        "channel": plan.channel,
        "title": plan.title,
        "max_items": plan.max_items,
        "wants_latest": plan.wants_latest,
    }
