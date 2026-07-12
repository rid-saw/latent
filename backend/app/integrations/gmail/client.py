"""Gmail API (readonly) — recent messages matching a block query."""

import asyncio
import re
from email.utils import parsedate_to_datetime

import httpx

from app.api.routes.auth import get_access_token
from app.models.schemas import ContentItem

BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

# Words that describe the *ask*, not the search ("newsletters about X in my inbox").
_FILLER = re.compile(
    r"\b(emails?|inbox|newsletters?|gmail|my|in|about|from|the|recent|latest|new)\b", re.I
)


def _gmail_query(query: str) -> str:
    terms = " ".join(w for w in _FILLER.sub(" ", query).split() if len(w) > 1)
    # Keep the briefing recent; fall back to unfiltered inbox if no terms remain.
    return f"{terms} newer_than:14d".strip()


def _from_name(raw: str) -> str:
    # 'Some Sender <a@b.com>' -> 'Some Sender'
    return raw.split("<")[0].strip().strip('"') or raw


async def search_messages(query: str, max_results: int = 5) -> list[ContentItem]:
    token = await get_access_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=15, headers=headers) as client:
        resp = await client.get(
            f"{BASE}/messages",
            params={"q": _gmail_query(query), "maxResults": max_results},
        )
        resp.raise_for_status()
        refs = resp.json().get("messages", [])

        async def fetch_one(ref: dict) -> ContentItem:
            r = await client.get(
                f"{BASE}/messages/{ref['id']}",
                params={
                    "format": "metadata",
                    "metadataHeaders": ["Subject", "From", "Date"],
                },
            )
            r.raise_for_status()
            msg = r.json()
            hdrs = {
                h["name"]: h["value"]
                for h in msg.get("payload", {}).get("headers", [])
            }
            try:
                short_date = parsedate_to_datetime(hdrs["Date"]).strftime("%d %b %Y")
            except (KeyError, ValueError, TypeError):
                short_date = ""
            return ContentItem(
                id=msg["id"],
                title=hdrs.get("Subject", "(no subject)"),
                url=f"https://mail.google.com/mail/u/0/#inbox/{msg['id']}",
                source="gmail",
                summary=msg.get("snippet"),
                meta=f"{_from_name(hdrs.get('From', ''))} · {short_date}",
            )

        return list(await asyncio.gather(*(fetch_one(r) for r in refs)))
