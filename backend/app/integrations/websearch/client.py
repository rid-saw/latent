"""General web search, through whichever provider CLI is already signed in.

This is the connector for anything the specific sources don't cover. No search
API key, no scraping: the CLI runs the search on the provider's own
infrastructure and reads the pages it finds.

It is the one connector that answers rather than points. Every other source
hands back things that already are pages — an email, a paper, a job ad — so a
link is the whole item. Here the block shows the answer itself, with the
source underneath, because "how do I make cold brew" deserves the method and
not a list of blogs that have it.

Two things follow from that:

The user's sentence must survive intact. Every other source is a keyword index
that needs short terms; this one is a language model and can act on detail the
others would choke on, so the request goes in verbatim with the supervisor's
structured answers alongside it rather than replacing it.

And the supervisor decides the shape first. A temperature is one value, a
recipe is ordered steps, rentals are rows with the same columns. One prompt
asking for "results" cannot produce all three, so the shape it chose is
spliced in and the answer comes back already in that form.
"""

import logging
import re
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from app.integrations.news.client import search_news
from app.models.schemas import ContentItem

PROMPT = """A personal-dashboard user asked for this, in their own words:

{request}

Read the whole thing. Any constraints, exclusions, amounts or preferences in \
that sentence are part of the request, not noise to be stripped out.
{context}
Answer it. Your answer goes on the block itself, with a link to your source \
underneath it, so the answer has to stand on its own. Never write "see the \
recipe here" or "according to this page" — give them the thing.

{shape}
Rules:
- Search the web and read the pages. Do not answer from memory alone.
- url is where you actually got it. Every result carries one, and it must be a
  page you really visited. Never invent a URL.
- Prefer the source closest to the facts over a roundup of other people's.
- If you genuinely cannot find it, return an empty list rather than guessing."""

# One per format the supervisor can choose. The block is drawn to match, so
# these decide the shape of the answer, not just its wording.
SHAPES = {
    "stat": """Format: a single value. Return exactly one result.
- title is the value itself, as short as it goes — "17°C", "A$4.2M", "1969"
- summary is what it is, five words at most — "Melbourne CBD, right now"
""",
    "text": """Format: prose. Return exactly one result.
- body is the explanation itself, two to four short paragraphs.
  No headings, no bullet points, no markdown.
- title is a short heading for it, five words at most
""",
    "bullets": """Format: {n} separate points. Order does not matter.
- one result per point, the point itself as the title
- keep each to one or two lines, a complete thought on its own
""",
    "steps": """Format: the steps of ONE method, in order, about {n} of them.
The order is the whole point.

- one result per step, the instruction itself as the title
- these are steps, not sources. "Brown 225g butter until it foams" is a step;
  "Brown Butter Cookies (Joy Food Sunshine)" is a recipe you found, and
  returning three of those is three recipes rather than one method.
- pick the single best method and give all of it, ingredients included where
  a step needs them
- keep quantities, times and temperatures inside the step rather than implied
- do not number them; their position is the number
""",
    "table": """Format: {n} rows, each one thing the user asked for.
- title is that thing's own name, not a headline or an article title
- fields must contain EXACTLY these keys and no others:
{keys}
- every value must be read off the page you took the row from, never recalled,
  estimated or inferred. Leave a field out entirely if the page does not say.
- url is that page, so each row can be checked. Drop any row you cannot cite.
""",
    "code": """Format: one snippet, ready to paste. Return exactly one result.
- body is the code and nothing else. No markdown fences, no commentary.
- title is a short description of what it does
- summary is one line of explanation, only if it isn't obvious from the code
""",
    "links": """Format: the {n} most useful pages to open and read.
- title is the page's own title
- summary is one sentence on what the page actually contains
""",
}

# YouTube topic blocks come through here, and they are the one case where a
# link really is the answer — you cannot put a video on a block. Kept as its
# own prompt rather than a rule bolted onto the one above, so that rewriting
# how the web answers questions can never quietly change what videos return.
VIDEO_PROMPT = """A personal-dashboard user asked for this, in their own words:

{request}

Read the whole thing. Any constraints or preferences in that sentence are part
of the request.
{context}
Find the {n} best YouTube videos for it.

Rules:
- Return ONLY YouTube video pages — links of the form youtube.com/watch.
  Never articles, roundups or listicles about videos.
- Only videos you actually found in this search. Never invent a URL.
- Prefer videos that answer the request directly over ones that merely mention it.
- If the search returns nothing usable, return an empty list."""


class _Hit(BaseModel):
    title: str
    url: str
    summary: str = ""
    published: str = Field(default="", description="Publication date if the page shows one")
    fields: dict[str, str] = Field(
        default_factory=dict,
        description="For format=table only: the named values for this row, "
        "using exactly the keys given",
    )
    body: str = Field(
        default="",
        description="For format=text or code only: the answer itself, when it "
        "is longer than a title",
    )


class _Hits(BaseModel):
    results: list[_Hit]


def _site(url: str) -> str:
    """example.com from https://www.example.com/a/b — shown as the item's source."""
    host = urlparse(url).netloc
    return host[4:] if host.startswith("www.") else host


_RANKING = {
    True: "the newest ones — recency matters more than relevance",
    False: "the most relevant ones — recency is secondary",
}


def plan_context(plan: dict | None) -> str:
    """The supervisor's structured answers, as context beside the request.

    These are additions, never substitutions: the model still reads the user's
    own sentence above and is free to disagree with anything here.
    """
    if not plan:
        return ""
    rows = []
    for label, key in (
        ("what they're after", "title"),
        ("place", "location"),
        ("channel or creator", "channel"),
    ):
        if plan.get(key):
            rows.append(f"- {label}: {plan[key]}")
    if plan.get("max_items"):
        rows.append(f"- how many they want: {plan['max_items']}")
    rows.append(f"- rank by: {_RANKING[bool(plan.get('wants_latest'))]}")
    return "\nAlso worked out from that same request:\n" + "\n".join(rows) + "\n"


def _shape(fmt: str, n: int, fields: list[str]) -> str:
    """The instruction for the layout the supervisor chose."""
    return SHAPES.get(fmt, SHAPES["links"]).format(
        n=n, keys="\n".join(f"    {f}" for f in fields)
    )


# Formats that are one answer, however many results come back.
_SINGLE = {"stat", "text", "code"}


async def _via_cli(
    query: str,
    max_results: int,
    plan: dict | None,
    videos_only: bool,
    fmt: str,
    fields: list[str],
) -> list[ContentItem]:
    from app.agents.llm import structured_llm  # lazy: avoid import cycle

    prompt = (
        VIDEO_PROMPT.format(request=query, n=max_results, context=plan_context(plan))
        if videos_only
        else PROMPT.format(
            request=query,
            context=plan_context(plan),
            shape=_shape(fmt, max_results, fields),
        )
    )
    hits = await structured_llm(prompt, _Hits, web=True)

    # A link is required of the formats that are lists of pages, because there
    # the link IS the item. For an answer it is a citation sitting under it, so
    # a missing one costs the source line, not the answer.
    needs_url = videos_only or fmt == "links"
    items = [
        ContentItem(
            id=h.url or h.title,
            title=h.title,
            url=h.url if h.url.startswith("http") else "",
            source="web",
            summary=h.summary or None,
            body=h.body or None,
            meta=" · ".join(p for p in (_site(h.url), h.published) if p),
            # Keep only the columns that were asked for, in the order they were
            # asked for. A model that invents one, drops one, or renames one
            # must not reshape the block — the supervisor decided that, so it
            # stays the same on every refresh.
            fields={f: h.fields[f] for f in fields if h.fields.get(f)} or None,
        )
        for h in hits.results
        if h.title and (h.url.startswith("http") or not needs_url)
    ]
    return items[:1] if fmt in _SINGLE else items[:max_results]


async def search_web(
    query: str,
    max_results: int = 3,
    *,
    plan: dict | None = None,
    videos_only: bool = False,
    fmt: str = "links",
    fields: list[str] | None = None,
) -> list[ContentItem]:
    """`query` is the user's own sentence, not extracted keywords.

    `plan` is the supervisor's structured fields, added as context. Callers
    without one (the no-LLM path, and refresh) simply omit it.

    `fmt` is the layout the supervisor chose — see SHAPES. It decides what
    comes back: one value, some prose, a set of steps, rows with columns.
    `fields` names the columns, and only applies to "table".
    """
    try:
        items = await _via_cli(query, max_results, plan, videos_only, fmt, fields or [])
    except Exception:
        logging.warning("web search unavailable, falling back to news", exc_info=True)
        items = []
    if items:
        return items
    if fmt != "links":
        return []
    return await search_news(_news_query(query), max_results=max_results)


_FILLER = re.compile(
    r"\b(i|would|like|want|to|the|a|an|of|for|and|with|in|on|at|about|all|any|"
    r"that|this|these|those|please|show|me|my|find|get|track|keep|up|"
    r"latest|recent|new|newest|over|under|within)\b",
    re.I,
)


def _news_query(request: str, limit: int = 8) -> str:
    words = [w for w in re.split(r"\W+", _FILLER.sub(" ", request)) if len(w) > 1]
    return " ".join(words[:limit]) or request
