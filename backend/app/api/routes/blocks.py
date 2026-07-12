"""Blocks CRUD, persisted in SQLite (single user until the auth phase)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import BlockRow, BriefingRow
from app.models.schemas import Block, BlockLayout, CreateBlockRequest
from app.services import blocks as svc

router = APIRouter(prefix="/api/blocks", tags=["blocks"])


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
    items, status = await svc.safe_fetch(row.query, row.source, row.max_items)  # type: ignore[arg-type]
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
