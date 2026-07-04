"""ESPN public JSON endpoints — league news, no key required.

Falls back to Google News for sports we can't map to an ESPN league.
"""

import httpx

from app.integrations.news.client import search_news
from app.models.schemas import ContentItem

NEWS_URL = "https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/news"

# keyword -> (sport, league)
LEAGUES: dict[str, tuple[str, str]] = {
    "nba": ("basketball", "nba"),
    "wnba": ("basketball", "wnba"),
    "nfl": ("football", "nfl"),
    "mlb": ("baseball", "mlb"),
    "nhl": ("hockey", "nhl"),
    "premier league": ("soccer", "eng.1"),
    "soccer": ("soccer", "eng.1"),
    "mls": ("soccer", "usa.1"),
    "champions league": ("soccer", "uefa.champions"),
    "f1": ("racing", "f1"),
    "formula": ("racing", "f1"),
    "golf": ("golf", "pga"),
    "college football": ("football", "college-football"),
}


def _match_league(query: str) -> tuple[str, str] | None:
    q = query.lower()
    for kw, pair in LEAGUES.items():
        if kw in q:
            return pair
    return None


async def search_sports(query: str, max_results: int = 5) -> list[ContentItem]:
    matched = _match_league(query)
    if not matched:
        return await search_news(f"sports {query}", max_results)

    sport, league = matched
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            NEWS_URL.format(sport=sport, league=league), params={"limit": max_results}
        )
    resp.raise_for_status()

    items: list[ContentItem] = []
    for article in resp.json().get("articles", [])[:max_results]:
        url = article.get("links", {}).get("web", {}).get("href", "")
        images = article.get("images") or []
        items.append(
            ContentItem(
                id=str(article.get("dataSourceIdentifier") or url),
                title=article.get("headline", ""),
                url=url,
                source="sports",
                summary=(article.get("description") or "")[:200] or None,
                meta=f"ESPN {league.upper()} · {article.get('published', '')[:10]}",
                thumbnail=images[0].get("url") if images else None,
            )
        )
    return items
