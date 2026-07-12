"""The Briefing: one agent-written briefing across all blocks."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.llm import agents_enabled
from app.agents.briefing import run_briefing
from app.db.database import get_db
from app.db.models import BlockRow, BriefingRow

router = APIRouter(prefix="/api/briefing", tags=["briefing"])

MAX_ITEMS_PER_BLOCK = 3


class Briefing(BaseModel):
    id: str
    text: str
    created_at: str


def _to_schema(row: BriefingRow) -> Briefing:
    # SQLite strips tzinfo; timestamps are UTC — say so, or JS parses as local.
    iso = row.created_at.isoformat()
    return Briefing(id=row.id, text=row.text, created_at=iso if "+" in iso else iso + "Z")


@router.get("")
def latest(page_id: str = "default", db: Session = Depends(get_db)) -> Briefing | None:
    row = (
        db.query(BriefingRow)
        .filter(BriefingRow.page_id == page_id)
        .order_by(BriefingRow.created_at.desc())
        .first()
    )
    return _to_schema(row) if row else None


@router.post("")
async def generate(page_id: str = "default", db: Session = Depends(get_db)) -> Briefing:
    if not agents_enabled():
        raise HTTPException(400, "No LLM backend — install Claude Code or set ANTHROPIC_API_KEY")

    rows = db.query(BlockRow).filter(BlockRow.page_id == page_id).all()
    blocks = [
        {
            "title": r.title,
            "query": r.query,
            "items": [
                " — ".join(p for p in (it.get("title"), it.get("meta"), (it.get("summary") or "")[:120]) if p)
                for it in (r.items or [])[:MAX_ITEMS_PER_BLOCK]
            ],
        }
        for r in rows
        if r.items
    ]
    if not blocks:
        raise HTTPException(400, "No blocks with content — create some blocks first")

    text = await run_briefing(blocks)
    row = BriefingRow(id=str(uuid.uuid4()), text=text, page_id=page_id)
    db.add(row)
    db.commit()
    return _to_schema(row)
