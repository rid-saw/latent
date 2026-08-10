"""The user's sentence reaches the two searches that can actually use it.

Every connector but these two is a keyword index: Gmail needs every word to
match, arXiv ANDs them together, Seek wants role words only. Compressing the
request is what makes those work at all. Web search and YouTube topic search
are a language model, and there the compression was throwing away the only
part it could have acted on — the constraints, amounts and exclusions people
put in a sentence and nowhere else.

So: those two get the request verbatim, and because there is then no keyword
to rewrite, they get one round instead of two.
"""

import pytest

from app.agents.graph import _after_critic
from app.agents.nodes.critic import Critique, critic_node
from app.agents.nodes.supervisor import Plan, searches_with_the_users_own_words
from app.integrations import websearch
from app.integrations.websearch.client import PROMPT, VIDEO_RULE, plan_context
from app.models.schemas import ContentItem

REQUEST = (
    "I would like to track all the art pieces publicly sold within Australia "
    "for over A$1M."
)


@pytest.mark.parametrize(
    "source,channel,expected",
    [
        ("web", "", True),
        ("youtube", "", True),          # a topic — nothing to read but a search
        ("youtube", "Fireship", False),  # a feed — the terms are never searched
        ("gmail", "", False),
        ("papers", "", False),
        ("jobs", "", False),
        ("news", "", False),
        ("sports", "", False),
    ],
)
def test_which_sources_search_with_the_users_own_words(source, channel, expected):
    assert searches_with_the_users_own_words(source, channel) is expected


async def test_the_supervisor_stores_the_request_itself_for_web(monkeypatch):
    """Not the model's summary of it — the sentence, unchanged.

    This is also what gets persisted on the block, so a refresh a week later
    searches with the same detail the first fetch had.
    """
    plan = Plan(source="web", search_terms="Australian art auction A$1M",
                title="Australian art sales", max_items=3, wants_latest=True)
    monkeypatch.setattr("app.agents.nodes.supervisor.structured_llm",
                        lambda *a, **k: _returns(plan))

    out = await _supervise(REQUEST)
    assert out["search_terms"] == REQUEST, "the squeezed version was stored instead"
    assert out["verbatim"] is True
    # The rest of the routing is untouched — it is only the terms that change.
    assert out["source"] == "web"
    assert out["max_items"] == 3
    assert out["wants_latest"] is True


async def test_keyword_sources_still_get_their_extracted_terms(monkeypatch):
    """The regression this change could easily cause: Gmail needs from:, not prose."""
    plan = Plan(source="gmail", search_terms="from:monash.edu",
                title="Monash mail", max_items=3, wants_latest=True)
    monkeypatch.setattr("app.agents.nodes.supervisor.structured_llm",
                        lambda *a, **k: _returns(plan))

    out = await _supervise("the most recent emails from monash uni please")
    assert out["search_terms"] == "from:monash.edu"
    assert out["verbatim"] is False


def test_the_request_appears_in_the_search_prompt_unaltered():
    body = PROMPT.format(request=REQUEST, n=3, context="", video_rule="")
    assert REQUEST in body, "the request was reworded on its way to the CLI"


def test_the_video_rule_lives_in_the_wrapper_not_the_request():
    """The old code prefixed 'YouTube videos: ' onto what the user wrote."""
    body = PROMPT.format(request=REQUEST, n=3, context="", video_rule=VIDEO_RULE)
    assert "youtube.com/watch" in body
    assert REQUEST in body
    assert "YouTube videos: I would like" not in body


def test_the_structured_fields_ride_alongside_the_request():
    text = plan_context(
        {"title": "Melbourne grad roles", "location": "Melbourne",
         "max_items": 5, "wants_latest": True}
    )
    assert "Melbourne grad roles" in text
    assert "place: Melbourne" in text
    assert "how many they want: 5" in text
    assert "newest" in text
    assert plan_context(None) == "", "callers without a plan add no context"


async def test_youtube_topic_search_sends_the_sentence_and_asks_for_videos(monkeypatch):
    seen = {}

    async def fake_search(query, max_results=3, *, plan=None, videos_only=False):
        seen.update(query=query, videos_only=videos_only, plan=plan)
        return [ContentItem(id="1", title="a video",
                            url="https://www.youtube.com/watch?v=abc12345678",
                            source="web")]

    monkeypatch.setattr(websearch.client, "search_web", fake_search)
    from app.integrations.youtube import client as yt
    monkeypatch.setattr(yt, "_details", lambda c, v: _details_ok())

    await yt.search_videos(REQUEST, max_results=2, plan={"max_items": 2})

    assert seen["query"] == REQUEST, "the request was decorated before searching"
    assert seen["videos_only"] is True, "without this the search returns articles"
    assert seen["plan"] == {"max_items": 2}


async def test_the_two_over_fetches_do_not_multiply(monkeypatch):
    """The graph already padded the count; padding the padding asked for 27.

    max_results arrives here already tripled (3 shown -> 9). Tripling again
    asked a search for 27 pages to fill a block of three and binned 24 of
    them a second later.
    """
    asked = {}

    async def fake_search(query, max_results=3, **kw):
        asked["n"] = max_results
        return []

    monkeypatch.setattr(websearch.client, "search_web", fake_search)
    from app.integrations.youtube import client as yt

    await yt.search_videos("a topic", max_results=9)
    assert asked["n"] == yt.MAX_WEB_PAGES == 12, "the over-fetches compounded again"

    # Small requests are untouched — the cap only bites once padding stacks.
    await yt.search_videos("a topic", max_results=3)
    assert asked["n"] == 9


async def test_a_verbatim_source_is_never_judged_so_never_loops(monkeypatch):
    """No critic call means no rejection, which means no second round.

    That falls out of the source gate rather than needing a rule of its own —
    and it protects the stored request, which the critic would otherwise be
    free to replace with keywords. That string is reused by every later
    refresh, so a rewrite would undo the verbatim change on the second fetch
    rather than the first.
    """
    def explode(*a, **k):
        raise AssertionError("the critic was called for a verbatim source")

    monkeypatch.setattr("app.agents.nodes.critic.structured_llm", explode)
    items = [ContentItem(id=str(i), title=f"item {i}", url="https://e.com",
                         source="web") for i in range(6)]

    out = await critic_node({"source": "web", "items": items, "query": REQUEST,
                             "max_items": 3, "search_terms": REQUEST})
    assert out == {"approved": True}, "no judgement, no rewrite, no round two"
    assert _after_critic({**out, "iterations": 1}) == "done"


def test_the_retry_loop_is_untouched_for_judged_sources():
    assert _after_critic({"approved": False, "iterations": 1}) == "refine"
    assert _after_critic({"approved": False, "iterations": 2}) == "done"
    assert _after_critic({"approved": True, "iterations": 1}) == "done"


# ── helpers ───────────────────────────────────────────────────────────────
async def _returns(value):
    return value


async def _details_ok():
    return ("a video", "Some Channel")


async def _supervise(query: str) -> dict:
    from app.agents.nodes.supervisor import supervisor_node

    return await supervisor_node({"query": query})
