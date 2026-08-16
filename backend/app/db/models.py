from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.models.schemas import Block


class PageRow(Base):
    __tablename__ = "pages"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    emoji: Mapped[str] = mapped_column(String, default="📄")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class BlockRow(Base):
    __tablename__ = "blocks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    page_id: Mapped[str] = mapped_column(String, default="default")
    title: Mapped[str] = mapped_column(String)
    query: Mapped[str] = mapped_column(String)
    # The supervisor's answers, whole. Individual columns for them kept
    # getting missed on refresh; see app/services/fetch.py.
    plan: Mapped[dict] = mapped_column(JSON, default=dict)
    source: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="ready")
    max_items: Mapped[int] = mapped_column(default=3)
    layout: Mapped[dict] = mapped_column(JSON)
    layout_v: Mapped[int] = mapped_column(default=2)  # 2 = 24-col/40px grid units
    items: Mapped[list] = mapped_column(JSON, default=list)  # cached last fetch
    # What each row shows besides its name, chosen once by the supervisor.
    # Stored for the same reason search_terms is: a refresh has to be able to
    # rebuild the block the agent designed. Without it a block of rental
    # listings quietly turned back into a list of links on the next refresh.
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def to_schema(self) -> Block:
        return Block.model_validate(
            {
                c: getattr(self, c)
                for c in (
                    "id", "page_id", "title", "query", "plan", "source",
                    "status", "max_items", "layout", "items",
                )
            }
        )

    @classmethod
    def from_schema(cls, block: Block) -> "BlockRow":
        return cls(**block.model_dump())


class BriefingRow(Base):
    __tablename__ = "briefings"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    page_id: Mapped[str] = mapped_column(String, default="default")
    text: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
