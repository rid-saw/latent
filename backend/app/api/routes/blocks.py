"""Blocks CRUD, persisted in SQLite (single user until the auth phase)."""

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.db.database import get_db
from app.db.models import BlockRow, BriefingRow
from app.models.schemas import Block, BlockLayout, CreateBlockRequest
from app.services import blocks as svc

router = APIRouter(prefix="/api/blocks", tags=["blocks"])


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


class _BlockGone(Exception):
    """The row was deleted while the agent was still working on it."""


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
        row.plan = block.plan
        row.max_items = block.max_items
        row.items = [i.model_dump() for i in block.items]
        row.status = status
        try:
            db.commit()
        except StaleDataError:
            db.rollback()
            raise _BlockGone from None
        return row.to_schema().model_dump()

    def _fail(status: int, detail: str) -> dict:
        """Mark the row failed and describe it, without failing a second time.

        Whatever went wrong may have left the session unusable, and committing
        on a poisoned session raises PendingRollbackError — which escapes the
        generator and drops the connection, so the client never receives the
        error it was in the middle of being sent. It sees a dead stream
        instead of "couldn't load this block".
        """
        db.rollback()
        payload: dict = {"status": status, "detail": detail}
        try:
            row.status = "error"
            db.commit()
            # Sent so the client can put the saved block on the grid rather
            # than losing the prompt along with the error.
            payload["block"] = row.to_schema().model_dump()
        except Exception:
            logging.warning("could not mark block %s failed", row.id, exc_info=True)
        return payload

    async def events() -> AsyncIterator[str]:
        # The id goes out first so the client can address the row immediately,
        # rather than holding a local placeholder until the agent returns.
        yield _sse("created", row.to_schema().model_dump())
        try:
            async for kind, payload in svc.create_block_streaming(row.query):
                if kind == "progress":
                    yield _sse("progress", {"message": payload})
                elif kind == "preview":
                    # Results as soon as the fetch returns, stored so an
                    # interruption here still leaves something useful.
                    yield _sse("preview", _update(payload, "loading"))  # type: ignore[arg-type]
                else:
                    yield _sse("block", _update(payload, payload.status))  # type: ignore[union-attr,arg-type]
        except _BlockGone:
            # Deleted while the agent was still working — a block takes up to
            # a minute to build, so there is plenty of time to give up on it.
            #
            # Said out loud rather than just closing the stream, because a
            # stream that stops without a result is indistinguishable from a
            # dropped connection, and the client recovers from that by putting
            # the block it was told about back on the grid. That resurrects
            # the very block the user deleted, as a copy the database has no
            # row for.
            logging.info("block %s was deleted while it was being built", row.id)
            yield _sse("gone", {"id": row.id})
        except HTTPException as e:
            yield _sse("error", _fail(e.status_code, e.detail))
        except Exception:
            logging.exception("block stream failed")
            yield _sse("error", _fail(500, "Block creation failed"))

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/stream")
async def create_block_stream(req: CreateBlockRequest, db: Session = Depends(get_db)):
    """Create a block, narrated over SSE while the agent works.

    Creation can take a minute. Streaming the graph's own steps turns that
    from a dead spinner into a visible pipeline — and surfaces what the agent
    decided to search for, which is otherwise invisible.
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
    # Refetch with the plan the agent produced, whole. Picking pieces of it
    # out by name is what let a refresh quietly return something plainer than
    # what was created — see app/services/fetch.py.
    plan = dict(row.plan or {})
    plan.setdefault("source", row.source)
    plan.setdefault("search_terms", row.query)
    plan.setdefault("max_items", row.max_items)
    items, status = await svc.safe_fetch(plan)
    row.items = [i.model_dump() for i in items]
    row.status = status
    try:
        db.commit()
    except StaleDataError:
        # Fetching takes seconds, and the block can be deleted while it runs —
        # by this user or another tab. The background sweep refreshes every
        # block on a timer, so deleting one mid-sweep hit this reliably. Gone
        # is not a server error, and the client already knows how to say so.
        db.rollback()
        raise HTTPException(404, "Block not found") from None
    return row.to_schema()


@router.delete("/{block_id}", status_code=204)
def delete_block(block_id: str, db: Session = Depends(get_db)) -> None:
    row = db.get(BlockRow, block_id)
    if row:
        # Invalidate the page's cached briefings — they summarized this block.
        db.query(BriefingRow).filter(BriefingRow.page_id == row.page_id).delete()
        db.delete(row)
        db.commit()
