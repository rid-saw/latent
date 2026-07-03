"""Blocks CRUD. In-memory store for this slice — DB lands with user auth."""

from fastapi import APIRouter, HTTPException

from app.models.schemas import Block, CreateBlockRequest
from app.services import blocks as svc

router = APIRouter(prefix="/api/blocks", tags=["blocks"])

_BLOCKS: dict[str, Block] = {}


@router.get("")
def list_blocks() -> list[Block]:
    return list(_BLOCKS.values())


@router.post("")
async def create_block(req: CreateBlockRequest) -> Block:
    block = await svc.create_block(req.query)
    _BLOCKS[block.id] = block
    return block


@router.post("/{block_id}/refresh")
async def refresh_block(block_id: str) -> Block:
    block = _BLOCKS.get(block_id)
    if not block:
        raise HTTPException(404, "Block not found")
    block.items, block.status = await svc.safe_fetch(block.query, block.source)
    return block


@router.delete("/{block_id}", status_code=204)
def delete_block(block_id: str) -> None:
    _BLOCKS.pop(block_id, None)
