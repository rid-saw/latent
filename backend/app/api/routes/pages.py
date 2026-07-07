"""Pages: named dashboards, each with its own blocks and rundown."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import BlockRow, PageRow, RundownRow
from app.models.schemas import CreatePageRequest, Page

router = APIRouter(prefix="/api/pages", tags=["pages"])


@router.get("")
def list_pages(db: Session = Depends(get_db)) -> list[Page]:
    rows = db.query(PageRow).order_by(PageRow.created_at).all()
    return [Page(id=r.id, name=r.name, emoji=r.emoji) for r in rows]


@router.post("")
def create_page(req: CreatePageRequest, db: Session = Depends(get_db)) -> Page:
    name = req.name.strip()
    if not name:
        raise HTTPException(400, "Page name can't be empty")
    # "emoji" holds an icon name (e.g. "newspaper") or a legacy emoji character.
    row = PageRow(id=str(uuid.uuid4()), name=name[:40], emoji=req.emoji[:32] or "file-text")
    db.add(row)
    db.commit()
    return Page(id=row.id, name=row.name, emoji=row.emoji)


@router.delete("/{page_id}", status_code=204)
def delete_page(page_id: str, db: Session = Depends(get_db)) -> None:
    if db.query(PageRow).count() <= 1:
        raise HTTPException(400, "Can't delete the last page")
    row = db.get(PageRow, page_id)
    if not row:
        return
    db.query(BlockRow).filter(BlockRow.page_id == page_id).delete()
    db.query(RundownRow).filter(RundownRow.page_id == page_id).delete()
    db.delete(row)
    db.commit()
