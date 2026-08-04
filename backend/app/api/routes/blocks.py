"""Blocks CRUD, persisted in SQLite (single user until the auth phase)."""

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import BlockRow, BriefingRow
from app.models.schemas import Block, BlockLayout, CreateBlockRequest
from app.services import blocks as svc

router = APIRouter(prefix="/api/blocks", tags=["blocks"])


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.get("")
def list_blocks(page_id: str | None = None, db: Session = Depends(get_db)) -> list[Block]:
    q = db.query(BlockRow).order_by(BlockRow.created_at)
    if page_id:
        q = q.filter(BlockRow.page_id == page_id)
    return [r.to_schema() for r in q.all()]


@router.post("")
async def create_block(req: CreateBlockRequest, db: Session = Depends(get_db)) -> Block:
    block = await svc.create_block(req.query)
    block.page_id = req.page_id
    db.add(BlockRow.from_schema(block))
    db.commit()
    return block


@router.post("/stream")
async def create_block_stream(req: CreateBlockRequest, db: Session = Depends(get_db)):
    """Same as POST /api/blocks, narrated over SSE while the agent works.

    Creation takes ~47s across two LLM calls. Streaming the graph's own steps
    turns that from a dead spinner into a visible pipeline — and surfaces what
    the agent decided to search for, which is otherwise invisible.
    """

    async def events() -> AsyncIterator[str]:
        try:
            async for kind, payload in svc.create_block_streaming(req.query):
                if kind == "progress":
                    yield _sse("progress", {"message": payload})
                    continue
                block: Block = payload  # type: ignore[assignment]
                block.page_id = req.page_id
                db.add(BlockRow.from_schema(block))
                db.commit()
                yield _sse("block", block.model_dump())
        except HTTPException as e:
            # The stream is already 200 by the time this fires, so the failure
            # has to travel as an event for the client to render it.
            yield _sse("error", {"status": e.status_code, "detail": e.detail})
        except Exception:
            logging.exception("block stream failed")
            yield _sse("error", {"status": 500, "detail": "Block creation failed"})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.patch("/layouts")
def save_layouts(layouts: dict[str, BlockLayout], db: Session = Depends(get_db)) -> dict:
    for block_id, layout in layouts.items():
        row = db.get(BlockRow, block_id)
        if row:
            row.layout = layout.model_dump()
    db.commit()
    return {"saved": len(layouts)}


@router.post("/{block_id}/refresh")
async def refresh_block(block_id: str, db: Session = Depends(get_db)) -> Block:
    row = db.get(BlockRow, block_id)
    if not row:
        raise HTTPException(404, "Block not found")
    # Reuse the supervisor's search terms. Falling back to the raw query is only
    # for blocks created before those were stored, or without an LLM backend.
    terms = row.search_terms or row.query
    items, status = await svc.safe_fetch(terms, row.source, row.max_items)  # type: ignore[arg-type]
    row.items = [i.model_dump() for i in items]
    row.status = status
    db.commit()
    return row.to_schema()


@router.delete("/{block_id}", status_code=204)
def delete_block(block_id: str, db: Session = Depends(get_db)) -> None:
    row = db.get(BlockRow, block_id)
    if row:
        # Invalidate the page's cached briefings — they summarized this block.
        db.query(BriefingRow).filter(BriefingRow.page_id == row.page_id).delete()
        db.delete(row)
        db.commit()
