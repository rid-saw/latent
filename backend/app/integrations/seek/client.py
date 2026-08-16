"""Seek job search — the JSON endpoint that powers seek.com.au, no key required.

Unofficial (same category as the ESPN endpoint): could change without notice,
in which case blocks degrade to status=error via safe_fetch. AU/NZ listings.

LinkedIn is deliberately absent: its jobs API is partner-only and scraping is
against its ToS — pin a LinkedIn search URL as a site block instead.
"""

import uuid

import httpx

from app.models.schemas import ContentItem

SEARCH_URL = "https://au.seek.com/api/jobsearch/v5/search"
JOB_URL = "https://www.seek.com.au/job/{id}"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def _meta(job: dict) -> str:
    company = (job.get("advertiser") or {}).get("description") or "Seek"
    locations = job.get("locations") or []
    location = locations[0].get("label", "") if locations else ""
    listed = (job.get("listingDate") or "")[:10]
    return " · ".join(p for p in (company, location, listed) if p)


def _summary(job: dict) -> str | None:
    return (job.get("teaser") or "")[:220] or None


def _fields(job: dict) -> dict[str, str]:
    """What a listing actually says, kept as values rather than run together.

    Seek returns these separately and they were being flattened into one grey
    line of prose. The bullet points in particular are the advertiser's own
    summary of the role and were dropped entirely.
    """
    out: dict[str, str] = {}
    if salary := job.get("salaryLabel"):
        out["salary"] = salary
    if work := [w for w in (job.get("workTypes") or []) if w]:
        out["type"] = ", ".join(work)
    if bullets := [b for b in (job.get("bulletPoints") or []) if b]:
        out["highlights"] = " · ".join(bullets[:3])
    return out


async def search_jobs(
    query: str, max_results: int = 3, location: str = "", latest: bool = False
) -> list[ContentItem]:
    params = {
        "siteKey": "AU-Main",
        "keywords": query,
        "pageSize": max_results,
    }
    if location:
        params["where"] = location
    if latest:
        params["sortmode"] = "ListedDate"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(SEARCH_URL, params=params, headers={"User-Agent": UA})
        resp.raise_for_status()
        jobs = resp.json().get("data", [])

    return [
        ContentItem(
            id=str(uuid.uuid4()),
            title=job.get("title", "Job listing"),
            url=JOB_URL.format(id=job["id"]),
            source="jobs",
            meta=_meta(job),
            summary=_summary(job),
            fields=_fields(job) or None,
            thumbnail=(job.get("branding") or {}).get("serpLogoUrl"),
        )
        for job in jobs[:max_results]
        if job.get("id")
    ]
