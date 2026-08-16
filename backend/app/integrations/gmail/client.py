"""Gmail API (readonly) — the N most recent messages matching a block query."""

import asyncio
from email.utils import parsedate_to_datetime

import httpx

from app.api.routes.auth import get_access_token
from app.models.schemas import ContentItem

BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


def _from_name(raw: str) -> str:
    # 'Some Sender <a@b.com>' -> 'Some Sender'
    return raw.split("<")[0].strip().strip('"') or raw


async def search_messages(query: str, max_results: int = 3) -> list[ContentItem]:
    token = await get_access_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=15, headers=headers) as client:
        # Gmail lists newest-first, so the first N matches are the N most
        # recent. No date window: the count *is* the recency control, and a
        # fixed window hid everything whenever a sender went quiet for a
        # fortnight. max_results comes from the user ("5 most recent…"),
        # defaulting to 3.
        resp = await client.get(
            f"{BASE}/messages",
            params={"q": query.strip(), "maxResults": max_results},
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
            sender = _from_name(hdrs.get("From", ""))
            return ContentItem(
                id=msg["id"],
                title=hdrs.get("Subject", "(no subject)"),
                url=f"https://mail.google.com/mail/u/0/#inbox/{msg['id']}",
                source="gmail",
                summary=msg.get("snippet"),
                # Who and when are the two things you scan an inbox by, so
                # they get their own values rather than being run together
                # into one line that has to be read to be understood.
                fields={
                    k: v for k, v in (("from", sender), ("date", short_date)) if v
                }
                or None,
            )

        return list(await asyncio.gather(*(fetch_one(r) for r in refs)))
