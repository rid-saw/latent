"""Human-readable progress lines for block creation.

Creating a block can take a minute. A spinner for that long reads as broken;
the same wait narrated reads as thinking. These lines are driven by real graph
events, not a timer — each one reports something that has actually happened.

One vocabulary, not one script per source: the graph already knows the source
and the search terms, so every message is a template with the right noun in
it. A new connector adds a row here, not a new set of messages.
"""

PLACE = {
    "gmail": "your inbox",
    "papers": "research papers",
    "youtube": "YouTube",
    "news": "the news",
    "sports": "scores and fixtures",
    "jobs": "job listings",
    "web": "the web",
    "site": "that page",
}

THINGS = {
    "gmail": "emails",
    "papers": "papers",
    "youtube": "videos",
    "news": "articles",
    "sports": "updates",
    "jobs": "listings",
    "web": "results",
    "site": "results",
}


def _things(source: str, n: int) -> str:
    plural = THINGS.get(source, "results")
    return plural if n != 1 else plural[:-1]


def routing() -> str:
    return "Working out where to look…"


def searching(source: str, terms: str) -> str:
    where = PLACE.get(source, "the web")
    if not terms:
        return f"Searching {where}"
    # web and youtube-topic search with the user's whole sentence, which can be
    # a paragraph. The search gets all of it; this line only has a card's width.
    shown = terms if len(terms) <= 64 else terms[:63].rstrip(" ,.;:") + "…"
    return f"Searching {where} for “{shown}”"


def finishing(source: str, n: int) -> str:
    if not n:
        return "Nothing came back"
    return f"Found {n} {_things(source, n)}"
