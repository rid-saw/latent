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


def _run_agent_into(db: Session, row: BlockRow) -> StreamingResponse:
    """Build `row.query` with the agent, folding each answer back into `row`.

    Shared by creating a block and rebuilding a failed one: it is the same
    minute of work either way, so it is the same code and the same narration.
    The only difference is who supplies the row.
    """

    def _update(block: Block, status: str) -> dict:
        """Fold the agent's latest answer into the row it started with."""
        row.title = block.title
        row.source = block.source
        row.search_terms = block.search_terms
        row.max_items = block.max_items
        row.items = [i.model_dump() for i in block.items]
        row.status = status
        db.commit()
        return row.to_schema().model_dump()

    async def events() -> AsyncIterator[str]:
        # The id goes out first so the client can address the row immediately,
        # rather than holding a local placeholder until the agent returns.
        yield _sse("created", row.to_schema().model_dump())
        try:
            async for kind, payload in svc.create_block_streaming(row.query):
                if kind == "progress":
                    yield _sse("progress", {"message": payload})
                elif kind == "preview":
                    # Raw results, before the critic has judged them. Stored,
                    # so an interruption here still leaves something useful.
                    yield _sse("preview", _update(payload, "loading"))  # type: ignore[arg-type]
                else:
                    yield _sse("block", _update(payload, payload.status))  # type: ignore[union-attr,arg-type]
        except HTTPException as e:
            row.status = "error"
            db.commit()
            yield _sse("error", {"status": e.status_code, "detail": e.detail,
                                 "block": row.to_schema().model_dump()})
        except Exception:
            logging.exception("block stream failed")
            row.status = "error"
            db.commit()
            yield _sse("error", {"status": 500, "detail": "Block creation failed",
                                 "block": row.to_schema().model_dump()})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/stream")
async def create_block_stream(req: CreateBlockRequest, db: Session = Depends(get_db)):
    """Create a block, narrated over SSE while the agent works.

    Creation takes ~47s across two LLM calls. Streaming the graph's own steps
    turns that from a dead spinner into a visible pipeline — and surfaces what
    the agent decided to search for, which is otherwise invisible.
    """
    # Written before any work starts. From here on the row exists, so a
    # dropped connection or a killed browser can no longer take the prompt
    # with it — the worst case is a row left at "loading", which the client
    # reads as interrupted and offers to retry.
    row = BlockRow.from_schema(svc.placeholder_block(req.query))
    row.page_id = req.page_id
    db.add(row)
    db.commit()
    return _run_agent_into(db, row)


@router.post("/{block_id}/rebuild")
async def rebuild_block(block_id: str, db: Session = Depends(get_db)):
    """Run the agent again for a block that never finished routing.

    Distinct from refresh, which refetches with search terms the agent already
    chose. A block that failed before routing has none, so there is nothing to
    refetch — it has to be built from the query again, which is the same work
    as creating it and so gets the same narration.
    """
    row = db.get(BlockRow, block_id)
    if not row:
        raise HTTPException(404, "Block not found")
    row.status = "loading"
    row.items = []
    db.commit()
    return _run_agent_into(db, row)


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
    # Refetching only. A block that never routed has nothing to refetch and
    # belongs on /rebuild, so this endpoint never spends an LLM call — which
    # matters because the background refresh calls it on every block.
    #
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
