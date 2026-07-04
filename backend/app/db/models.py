from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.models.schemas import Block


class BlockRow(Base):
    __tablename__ = "blocks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    query: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="ready")
    max_items: Mapped[int] = mapped_column(default=5)
    layout: Mapped[dict] = mapped_column(JSON)
    items: Mapped[list] = mapped_column(JSON, default=list)  # cached last fetch
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def to_schema(self) -> Block:
        return Block.model_validate(
            {
                c: getattr(self, c)
                for c in ("id", "title", "query", "source", "status", "max_items", "layout", "items")
            }
        )

    @classmethod
    def from_schema(cls, block: Block) -> "BlockRow":
        return cls(**block.model_dump())


class RundownRow(Base):
    __tablename__ = "rundowns"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    text: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
