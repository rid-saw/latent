"""A block's row exists from the moment it is asked for, and retrying is a
separate job from refreshing.

Two rules the routes have to keep:

The row is written before any agent work starts, so a dropped connection or a
killed browser cannot take the prompt with it. Prompts take thought to write;
losing one to a rate limit used to mean retyping it.

And refresh refetches, while rebuild re-routes. A block that failed before the
supervisor ran has no search terms and so nothing to refetch — it belongs on
/rebuild. Keeping that out of /refresh matters because the half-hourly
background refresh calls /refresh on every block, and an LLM call hidden in
there would quietly burn the user's usage limit.
"""

import pytest
from fastapi import HTTPException

from app.api.routes import blocks as routes
from app.models.schemas import Block, BlockLayout, ContentItem
from app.services import blocks as svc


class FakeRow:
    """Stand-in for BlockRow: only the fields the routes touch."""

    def __init__(self, **kw):
        self.id = "b1"
        self.query = "emails from monash uni"
        self.plan: dict = {}
        self.source = "gmail"
        self.status = "error"
        self.max_items = 3
        self.items: list = []
        self.title = "Monash Uni Emails"
        self.__dict__.update(kw)

    def to_schema(self) -> Block:
        return Block(
            id=self.id, title=self.title, query=self.query,
            plan=self.plan, source=self.source,
            layout=BlockLayout(x=0, y=0, w=8, h=8),
            items=[ContentItem(**i) for i in self.items],
            status=self.status, max_items=self.max_items,
        )


class FakeDB:
    def __init__(self, row=None):
        self.row = row
        self.added: list = []
        self.commits = 0

    def get(self, _model, _id):
        return self.row

    def add(self, row):
        self.added.append(row)

    def commit(self):
        self.commits += 1


@pytest.fixture
def never_calls_the_agent(monkeypatch):
    """Fail loudly if a code path reaches for the LLM when it shouldn't."""

    async def boom(query: str):
        raise AssertionError("this path must not spend an LLM call")

    monkeypatch.setattr(svc, "create_block", boom)


# ── the row exists before any work ──────────────────────────────────────────

def test_placeholder_is_written_before_the_agent_decides_anything():
    b = svc.placeholder_block("emails from monash uni about enrolment")
    assert b.query == "emails from monash uni about enrolment"
    assert b.status == "loading", "the row exists while the agent is still working"
    assert b.items == []
    assert b.plan == {}, "an empty plan is the signal that routing never ran"


def test_placeholder_guesses_a_source_from_the_words():
    """Only to size the card; routing replaces it a moment later."""
    assert svc.placeholder_block("recent papers on AI").source == "papers"
    assert svc.placeholder_block("https://example.com").source == "site"


async def test_create_commits_the_row_before_streaming(monkeypatch):
    db = FakeDB()

    async def never_runs(query):
        raise AssertionError("the row must be committed before the agent starts")
        yield  # pragma: no cover

    monkeypatch.setattr(svc, "create_block_streaming", never_runs)
    from app.models.schemas import CreateBlockRequest

    await routes.create_block_stream(
        CreateBlockRequest(query="best headphones"), db  # type: ignore[arg-type]
    )
    assert len(db.added) == 1, "the row is added"
    assert db.commits >= 1, "and committed, before anything is streamed"


# ── refresh refetches; it never re-routes ───────────────────────────────────

async def test_refresh_never_runs_the_agent(monkeypatch, never_calls_the_agent):
    """Even for the block most tempting to re-route: failed, and no terms."""
    row = FakeRow(status="error", plan={})
    db = FakeDB(row)

    async def fake_fetch(plan):
        assert plan["search_terms"] == "emails from monash uni", "falls back to the raw query"
        return [], "error"

    monkeypatch.setattr(svc, "safe_fetch", fake_fetch)
    await routes.refresh_block("b1", db)  # type: ignore[arg-type]


async def test_refresh_uses_the_stored_search_terms(monkeypatch, never_calls_the_agent):
    row = FakeRow(status="ready", plan={"search_terms": "from:monash.edu"})
    db = FakeDB(row)

    async def fake_fetch(plan):
        assert plan["search_terms"] == "from:monash.edu"
        return [ContentItem(id="m1", title="Enrolment", url="https://x", source="gmail")], "ready"

    monkeypatch.setattr(svc, "safe_fetch", fake_fetch)
    out = await routes.refresh_block("b1", db)  # type: ignore[arg-type]
    assert out.status == "ready"
    assert len(out.items) == 1


# ── rebuild re-routes, in place ─────────────────────────────────────────────

async def test_rebuild_clears_the_row_and_keeps_its_id(monkeypatch):
    row = FakeRow(status="error", items=[{"id": "old", "title": "stale",
                                          "url": "https://x", "source": "gmail"}])
    db = FakeDB(row)

    async def never_runs(query):
        assert query == "emails from monash uni", "rebuild reuses the saved prompt"
        raise AssertionError("stop before the agent")
        yield  # pragma: no cover

    monkeypatch.setattr(svc, "create_block_streaming", never_runs)
    await routes.rebuild_block("b1", db)  # type: ignore[arg-type]

    assert row.status == "loading", "shows as working while it runs"
    assert row.items == [], "stale results cleared before the new run"
    assert row.id == "b1", "same row, so the block keeps its place on the grid"
    assert not db.added, "rebuild updates in place, it does not insert a second row"


async def test_rebuild_404s_for_a_block_that_is_gone():
    db = FakeDB(None)
    with pytest.raises(HTTPException) as caught:
        await routes.rebuild_block("nope", db)  # type: ignore[arg-type]
    assert caught.value.status_code == 404


async def test_refresh_keeps_the_shape_the_agent_chose(monkeypatch, never_calls_the_agent):
    """A block of rental listings must not come back as a list of links.

    The field list is what turns web results from pages into things. It was
    stored nowhere, so every refresh rebuilt the block without it — and the
    background sweep meant that happened on a timer, silently.
    """
    row = FakeRow(source="youtube", status="ready", plan={
        "source": "youtube", "search_terms": "Fireship", "channel": "Fireship",
        "format": "links", "fields": [], "max_items": 3, "wants_latest": True,
    })
    db = FakeDB(row)
    seen = {}

    async def fake_fetch(plan):
        seen.update(plan)
        return [], "ready"

    monkeypatch.setattr(svc, "safe_fetch", fake_fetch)
    await routes.refresh_block("b1", db)  # type: ignore[arg-type]
    # channel is the one that had no column of its own, so every refresh
    # dropped it and the block web-searched for old videos instead of
    # reading the channel's feed.
    assert seen["channel"] == "Fireship"
    assert seen["wants_latest"] is True
    assert seen["search_terms"] == "Fireship"


async def test_refresh_404s_when_the_block_is_deleted_mid_fetch(monkeypatch,
                                                                never_calls_the_agent):
    """Fetching takes seconds and the block can be deleted while it runs.

    The background sweep refreshes every block on a timer, so deleting one
    mid-sweep raced the write and surfaced as a 500. Gone is not a server
    error, and the client already has a sentence for it.
    """
    from sqlalchemy.orm.exc import StaleDataError

    row = FakeRow(status="ready", plan={"search_terms": "from:monash.edu"})
    db = FakeDB(row)

    async def fake_fetch(plan):
        return [], "ready"

    def deleted_underneath():
        raise StaleDataError("UPDATE expected to update 1 row(s); 0 were matched.")

    db.commit = deleted_underneath  # type: ignore[method-assign]
    db.rollback = lambda: None  # type: ignore[attr-defined]
    monkeypatch.setattr(svc, "safe_fetch", fake_fetch)

    with pytest.raises(HTTPException) as caught:
        await routes.refresh_block("b1", db)  # type: ignore[arg-type]
    assert caught.value.status_code == 404


# ── deleting a block while it is being built ────────────────────────────────

async def _drain(response) -> list[str]:
    return [chunk async for chunk in response.body_iterator]


async def test_deleting_a_block_mid_build_ends_the_stream_quietly(monkeypatch):
    """A block takes up to a minute to build and its card sits on the grid the
    whole time, so there is plenty of room to change your mind.

    The write then hits a row that no longer exists. That is not a failure to
    report — the client asked for it and has already removed the card.
    """
    from sqlalchemy.orm.exc import StaleDataError

    row = FakeRow(status="loading")
    db = FakeDB(row)

    def deleted_underneath():
        raise StaleDataError("UPDATE expected to update 1 row(s); 0 were matched.")

    db.commit = deleted_underneath  # type: ignore[method-assign]
    db.rollback = lambda: None  # type: ignore[attr-defined]

    async def one_preview(query):
        yield "preview", Block(
            id="b1", title="t", query=query, source="gmail",
            layout=BlockLayout(x=0, y=0, w=8, h=8), items=[], status="loading",
        )

    monkeypatch.setattr(svc, "create_block_streaming", one_preview)
    chunks = await _drain(routes._run_agent_into(db, row))  # type: ignore[arg-type]

    assert any("event: created" in c for c in chunks), "the id still went out first"
    assert not any("event: error" in c for c in chunks), "a deliberate delete is not an error"
    # Said out loud, because a stream that just stops looks exactly like a
    # dropped connection — and the client recovers from that by putting the
    # block back on the grid, resurrecting the one just deleted.
    assert any("event: gone" in c for c in chunks), "the client is told it is gone"


async def test_a_poisoned_session_still_delivers_the_error(monkeypatch):
    """The failure handler used to commit on a session the failure had already
    broken. That raised PendingRollbackError, escaped the generator and dropped
    the connection — so the client saw a dead stream instead of the error it
    was about to be handed, and the prompt went with it.
    """
    row = FakeRow(status="loading")
    db = FakeDB(row)
    rolled_back = {"n": 0}

    def poisoned():
        raise RuntimeError("this session is unusable until it is rolled back")

    db.commit = poisoned  # type: ignore[method-assign]
    db.rollback = lambda: rolled_back.__setitem__("n", rolled_back["n"] + 1)  # type: ignore[attr-defined]

    async def blows_up(query):
        raise RuntimeError("the connector fell over")
        yield  # pragma: no cover

    monkeypatch.setattr(svc, "create_block_streaming", blows_up)
    chunks = await _drain(routes._run_agent_into(db, row))  # type: ignore[arg-type]

    errors = [c for c in chunks if "event: error" in c]
    assert errors, "the client is told, even when the session is broken"
    assert "Block creation failed" in errors[0]
    assert rolled_back["n"] >= 1, "rolled back before trying to write again"


# ── the plan travels whole ──────────────────────────────────────────────────

def test_the_plan_carries_every_decision_the_agent_made():
    """The bug this exists to prevent, three times over.

    Each of these was stored as its own column or not at all, and the ones
    without a column were dropped on the first refresh: a Fireship block
    stopped reading the channel's upload feed and web-searched five-year-old
    videos, a table of rentals came back as a list of links, and a Melbourne
    job search lost Melbourne. The dashboard refreshes on a timer, so each
    one was correct when made and wrong minutes later.
    """
    state = {
        "query": "latest Fireship videos",
        "source": "youtube",
        "search_terms": "Fireship",
        "channel": "Fireship",
        "location": "",
        "wants_latest": True,
        "format": "links",
        "fields": [],
        "max_items": 3,
        "title": "Fireship",
        "verbatim": False,
        "items": [],
    }
    block = svc._block_from(state, state["query"], status="ready")

    for decision in ("channel", "wants_latest", "search_terms", "format",
                     "fields", "max_items", "source"):
        assert decision in block.plan, f"{decision} would be lost on refresh"
    # The prompt and the results are not decisions and live on the block itself.
    assert "query" not in block.plan
    assert "items" not in block.plan


async def test_a_new_agent_decision_needs_no_new_column():
    """The point of storing the plan whole: the next thing the supervisor
    learns to decide is carried without anyone remembering to add a column."""
    state = {"query": "q", "source": "web", "search_terms": "q",
             "max_items": 3, "something_invented_next_week": "kept"}
    block = svc._block_from(state, "q", status="ready")
    assert block.plan["something_invented_next_week"] == "kept"
