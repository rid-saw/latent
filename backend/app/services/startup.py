"""Startup refresh: refetch every block's content, then write one fresh rundown.

Runs once per backend start. Block refreshes hit only the free content APIs
(routing is already stored per block); the LLM is used just for the briefing.
Page reloads serve this cached state — nothing re-runs until the next startup
or a manual per-block refresh.
"""

import asyncio
import logging
import uuid

from app.agents.llm import agents_enabled
from app.db.database import SessionLocal
from app.db.models import BlockRow, RundownRow
from app.services import blocks as svc

log = logging.getLogger("startup")


async def refresh_all_and_brief() -> None:
    db = SessionLocal()
    try:
        rows = db.query(BlockRow).all()
        if not rows:
            return

        log.info("refreshing %d blocks…", len(rows))
        results = await asyncio.gather(
            *(svc.safe_fetch(r.query, r.source, r.max_items) for r in rows)
        )
        for row, (items, status) in zip(rows, results):
            row.items = [i.model_dump() for i in items]
            row.status = status
        db.commit()
        log.info("blocks refreshed")

        if agents_enabled():
            from app.agents.rundown import payload_from_rows, run_rundown

            payload = payload_from_rows(rows)
            if payload:
                text = await run_rundown(payload)
                db.add(RundownRow(id=str(uuid.uuid4()), text=text))
                db.commit()
                log.info("rundown written")
    except Exception:
        log.exception("startup refresh failed")
    finally:
        db.close()
