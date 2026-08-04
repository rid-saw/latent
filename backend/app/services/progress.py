"""Human-readable progress lines for block creation.

Creating a block runs two LLM calls and takes ~47s. A spinner for that long
reads as broken; the same wait narrated reads as thinking. These lines are
driven by real graph events, not a timer — each one reports something that
has actually happened.

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
    return f"Searching {where} for “{terms}”" if terms else f"Searching {where}"


def reviewing(source: str, n: int) -> str:
    if not n:
        return "Nothing came back — checking"
    return f"Reviewing {n} {_things(source, n)}"


def refining(terms: str) -> str:
    return f"Not quite right — trying “{terms}” instead"


def finishing(source: str, n: int) -> str:
    return f"Keeping the best {n} {_things(source, n)}"
