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

For web: `format` decides how the answer appears on the block. The block IS \
the answer — not a list of places to go and find it. Pick the shape the answer \
naturally takes.

  stat     one value is the whole answer
           "what's the temperature in Melbourne" · "AUD to USD right now"

  text     an explanation, written as prose
           "how does superannuation work" · "why is the sky blue"

  bullets  several short points where order does not matter
           "three facts about Roman history" · "what's new in Python 3.14"

  steps    an ordered procedure where order does matter
           "how do I make cold brew" · "brown butter chocolate chip cookies"
           set max_items to however many steps the method really takes

  table    several of the same kind of thing, compared on the same columns
           "homes for rent in Melbourne CBD under $400 a week"
           "all the paintings sold in Australia for over $1M"

  code     a snippet the user will copy
           "how do I reverse a list in Python"

  links    pages worth opening in full, where summarising loses the point
           "best noise-cancelling headphones under $300"

Only `table` uses `fields`: 1-4 lowercase column names — "price", "bedrooms", \
"address". Never the thing's own name, that is its title. Never a link, source \
or url, every row carries one automatically. Leave `fields` empty for every \
other format.

`links` is the last resort, not the default. Reach for it only when the value \
really is in opening the page — a long review, an argument, something visual. \
If the question has an answer, answer it.

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
        le=20,
        description="How many items the answer needs: the number they named, "
        "or for steps and bullets however many the answer actually takes (a "
        "recipe is 6-12 steps). Otherwise 3.",
    )
    wants_latest: bool = Field(
        description="True if the user wants the newest/most recent items "
        "(e.g. 'latest', 'newest', 'new videos from X') rather than the most relevant"
    )
    format: Literal[
        "links", "text", "bullets", "steps", "table", "stat", "code"
    ] = Field(
        default="links",
        description="For web only: how the answer should be laid out on the "
        "block. See the seven options above; pick the shape the answer "
        "naturally takes, and only fall back to 'links' when reading the page "
        "is genuinely the point.",
    )
    fields: list[str] = Field(
        default_factory=list,
        description="For format='table' only: 1-4 lowercase column names "
        "('paintings sold over $1M' -> ['artist', 'price', 'date']). Empty "
        "for every other format.",
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
        # Only web chooses a layout. Every other source returns pages, so
        # "links" is the only shape that fits, and asking one of them for
        # columns would promise something its API cannot fill.
        "format": plan.format if plan.source == "web" else "links",
        "fields": plan.fields if plan.source == "web" and plan.format == "table" else [],
    }
