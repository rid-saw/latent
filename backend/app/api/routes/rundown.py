"""The Rundown: one agent-written briefing across all blocks."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.llm import agents_enabled
from app.agents.rundown import run_rundown
from app.db.database import get_db
from app.db.models import BlockRow, RundownRow

router = APIRouter(prefix="/api/rundown", tags=["rundown"])

MAX_ITEMS_PER_BLOCK = 5


class Rundown(BaseModel):
    id: str
    text: str
    created_at: str


def _to_schema(row: RundownRow) -> Rundown:
    return Rundown(id=row.id, text=row.text, created_at=row.created_at.isoformat())


@router.get("")
def latest(db: Session = Depends(get_db)) -> Rundown | None:
    row = db.query(RundownRow).order_by(RundownRow.created_at.desc()).first()
    return _to_schema(row) if row else None


@router.post("")
async def generate(db: Session = Depends(get_db)) -> Rundown:
    if not agents_enabled():
        raise HTTPException(400, "No LLM backend — install Claude Code or set ANTHROPIC_API_KEY")

    rows = db.query(BlockRow).all()
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

    text = await run_rundown(blocks)
    row = RundownRow(id=str(uuid.uuid4()), text=text)
    db.add(row)
    db.commit()
    return _to_schema(row)
