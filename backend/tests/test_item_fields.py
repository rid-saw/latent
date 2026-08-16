"""A block holds the answer, not directions to it.

Every block used to be a list of pages: a URL, a headline, a line of summary.
That suits "best headphones under $300", where reading the review is the
point. It suits nothing else. "How do I make cold brew" wants the method,
"what's the temperature" wants a number, and "paintings sold for over $1M"
wants the sales.

So the supervisor picks a layout and the search answers in that shape. The
connectors that already know their own shape — a paper has citations, a job
has a salary — fill their fields directly, and both were fetching those and
throwing them away.
"""

import pytest

from app.integrations.papers.client import _paper_fields
from app.integrations.seek.client import _fields as _job_fields
from app.integrations.websearch.client import PROMPT, _shape
from app.models.schemas import ContentItem


# ── the row itself ────────────────────────────────────────────────────────
def test_a_row_does_not_have_to_be_a_page():
    """A sale is not a URL. The item model used to require one."""
    sale = ContentItem(id="1", title="Blue Poles", source="web",
                       fields={"price": "A$4.2M"})
    assert sale.url == ""
    assert sale.fields == {"price": "A$4.2M"}


# ── what the web search is asked for ──────────────────────────────────────
@pytest.mark.parametrize(
    "fmt,expected",
    [
        ("links", "most useful pages to open"),
        ("stat", "a single value"),
        ("text", "body is the explanation itself"),
        ("bullets", "separate points"),
        ("steps", "in order"),
        ("code", "ready to paste"),
        ("table", "each one thing the user asked for"),
    ],
)
def test_every_format_asks_for_something_different(fmt, expected):
    assert expected in _shape(fmt, 3, ["price"])


def test_an_unknown_format_falls_back_to_links():
    """A layout the search doesn't recognise must still produce a block."""
    assert _shape("interpretive-dance", 3, []) == _shape("links", 3, [])


def test_a_table_lists_its_columns_for_the_model():
    body = _shape("table", 5, ["artist", "price", "auction house"])
    for f in ("artist", "price", "auction house"):
        assert f"    {f}" in body


def test_rows_must_be_citable_and_never_recalled():
    """The failure mode here is worse than a bad link, so it is spelled out.

    A fabricated URL is obvious the moment it 404s. "Blue Poles, A$4.2M,
    Sotheby's, 3 March" reads exactly like a real sale and would sit on the
    dashboard indefinitely.
    """
    body = PROMPT.format(request="q", shape=_shape("table", 3, ["price"]), context="")
    assert "never recalled" in body
    assert "Drop any row you cannot cite" in body
    assert "Never invent a URL" in body


def test_the_answer_must_stand_on_its_own():
    """The whole point: a recipe block holds the recipe, not a note saying
    where the recipe is."""
    body = PROMPT.format(request="q", shape=_shape("steps", 8, []), context="")
    assert "give them the thing" in body
    assert "see the" in body and "according to this page" in body


# ── connectors that already knew their shape ──────────────────────────────
def test_papers_keep_the_citation_count():
    """"Recent high-traffic papers" was the request this project started from,
    and the traffic number was already in every response, discarded."""
    fields = _paper_fields(
        {
            "cited_by_count": 514,
            "authorships": [
                {"author": {"display_name": "A Ng"}},
                {"author": {"display_name": "B Li"}},
            ],
            "open_access": {"is_oa": True},
            "topics": [{"display_name": "Machine Learning"}],
        }
    )
    assert fields == {
        "citations": "514",
        "authors": "A Ng +1",
        "access": "open",
        "topic": "Machine Learning",
    }


def test_papers_with_nothing_extra_add_no_fields():
    assert _paper_fields({}) == {}
    assert _paper_fields({"cited_by_count": 0}) == {"citations": "0"}, "zero is a fact"


ARXIV_XML = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2601.00001</id>
    <title>Agentic AI in Medicine</title>
    <summary>An overview.</summary>
    <published>2026-01-02T00:00:00Z</published>
    <author><name>A Ng</name></author>
    <author><name>B Li</name></author>
    <arxiv:primary_category term="cs.AI"/>
  </entry>
</feed>"""


async def test_the_arxiv_fallback_has_fields_of_its_own(monkeypatch):
    """OpenAlex rate-limits often enough that this is a normal path.

    Without fields here, a 429 upstream quietly turns a populated card into a
    bare one — which is exactly what happened while building this.
    """
    import httpx

    from app.integrations.arxiv import client as arxiv

    transport = httpx.MockTransport(lambda r: httpx.Response(200, text=ARXIV_XML))
    original = httpx.AsyncClient
    monkeypatch.setattr(
        arxiv.httpx, "AsyncClient",
        lambda *a, **kw: original(*a, **{**kw, "transport": transport}),
    )

    items = await arxiv.search_papers("anything", 1)
    assert items[0].fields == {"access": "open (preprint)", "authors": "A Ng +1"}


def test_jobs_keep_the_advertisers_own_bullet_points():
    fields = _job_fields(
        {
            "salaryLabel": "$70k – $85k",
            "workTypes": ["Full time"],
            "bulletPoints": ["Fully funded tuition", "Career change into tech",
                             "Global consultancy", "A fourth one"],
        }
    )
    assert fields["salary"] == "$70k – $85k"
    assert fields["type"] == "Full time"
    assert fields["highlights"] == (
        "Fully funded tuition · Career change into tech · Global consultancy"
    ), "capped at three so one listing cannot fill the card"


def test_a_listing_with_no_extras_adds_no_fields():
    assert _job_fields({"title": "Engineer"}) == {}


# ── the model does not get to reshape the block ───────────────────────────
@pytest.mark.parametrize(
    "returned,expected",
    [
        # Renamed a field
        ({"artist": "Pollock", "cost": "A$4.2M"}, {"artist": "Pollock"}),
        # Invented one
        ({"artist": "Pollock", "price": "A$4.2M", "mood": "bold"},
         {"artist": "Pollock", "price": "A$4.2M"}),
        # Left one blank
        ({"artist": "Pollock", "price": ""}, {"artist": "Pollock"}),
    ],
)
def test_only_the_requested_fields_survive(returned, expected):
    """The supervisor picked the columns so they stay the same on every
    refresh. A model that renames or invents one must not reshape the block."""
    asked = ["artist", "price"]
    kept = {f: returned[f] for f in asked if returned.get(f)}
    assert kept == expected


# ── one answer, or several rows ───────────────────────────────────────────
@pytest.mark.parametrize("fmt", ["stat", "text", "code"])
async def test_a_single_answer_stays_single(fmt, monkeypatch):
    """A temperature is one number however many pages mention it."""
    from app.integrations.websearch import client as ws

    async def four(prompt, schema, web=False):
        return ws._Hits(results=[
            ws._Hit(title=f"answer {i}", url=f"https://e.com/{i}", body="x")
            for i in range(4)
        ])

    monkeypatch.setattr("app.agents.llm.structured_llm", four)
    items = await ws.search_web("q", 3, fmt=fmt)
    assert len(items) == 1


@pytest.mark.parametrize("fmt", ["bullets", "steps", "table", "links"])
async def test_a_list_answer_keeps_its_rows(fmt, monkeypatch):
    from app.integrations.websearch import client as ws

    async def four(prompt, schema, web=False):
        return ws._Hits(results=[
            ws._Hit(title=f"row {i}", url=f"https://e.com/{i}") for i in range(4)
        ])

    monkeypatch.setattr("app.agents.llm.structured_llm", four)
    assert len(await ws.search_web("q", 3, fmt=fmt)) == 3, "trimmed to what was asked"


async def test_an_answer_survives_without_a_link_but_a_page_does_not(monkeypatch):
    """For links the URL is the item, so a result without one is nothing. For
    an answer it is a citation underneath, so a missing one costs the source
    line rather than the answer."""
    from app.integrations.websearch import client as ws

    async def uncited(prompt, schema, web=False):
        return ws._Hits(results=[ws._Hit(title="17°C", url="", summary="Melbourne")])

    monkeypatch.setattr("app.agents.llm.structured_llm", uncited)

    assert len(await ws.search_web("q", 3, fmt="stat")) == 1, "the answer survives"
    assert await ws.search_web("q", 3, fmt="links") == [], "the page does not"
