"""Blocks CRUD, persisted in SQLite (single user until the auth phase)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import BlockRow
from app.models.schemas import Block, BlockLayout, CreateBlockRequest
from app.services import blocks as svc

router = APIRouter(prefix="/api/blocks", tags=["blocks"])


@router.get("")
def list_blocks(db: Session = Depends(get_db)) -> list[Block]:
    rows = db.query(BlockRow).order_by(BlockRow.created_at).all()
    return [r.to_schema() for r in rows]


@router.post("")
async def create_block(req: CreateBlockRequest, db: Session = Depends(get_db)) -> Block:
    block = await svc.create_block(req.query)
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
        db.delete(row)
        db.commit()
