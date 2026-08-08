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
        self.search_terms = ""
        self.source = "gmail"
        self.status = "error"
        self.max_items = 3
        self.items: list = []
        self.title = "Monash Uni Emails"
        self.__dict__.update(kw)

    def to_schema(self) -> Block:
        return Block(
            id=self.id, title=self.title, query=self.query,
            search_terms=self.search_terms, source=self.source,
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
    assert b.search_terms == "", "no terms is the signal that routing never ran"


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
    row = FakeRow(status="error", search_terms="")
    db = FakeDB(row)

    async def fake_fetch(terms, source, max_items):
        assert terms == "emails from monash uni", "falls back to the raw query"
        return [], "error"

    monkeypatch.setattr(svc, "safe_fetch", fake_fetch)
    await routes.refresh_block("b1", db)  # type: ignore[arg-type]


async def test_refresh_uses_the_stored_search_terms(monkeypatch, never_calls_the_agent):
    row = FakeRow(status="ready", search_terms="from:monash.edu")
    db = FakeDB(row)

    async def fake_fetch(terms, source, max_items):
        assert terms == "from:monash.edu"
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
