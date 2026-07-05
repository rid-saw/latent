from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, blocks, pages, rundown
from app.config import settings
from sqlalchemy import text

from app.db import models  # noqa: F401 — register tables
from app.db.database import Base, engine

Base.metadata.create_all(engine)

# Micro-migrations: create_all doesn't add columns to existing tables.
with engine.connect() as _conn:
    def _add_column(table: str, column: str, ddl: str) -> None:
        cols = [r[1] for r in _conn.execute(text(f"PRAGMA table_info({table})"))]
        if column not in cols:
            _conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))

    _add_column("blocks", "max_items", "max_items INTEGER NOT NULL DEFAULT 3")
    _add_column("blocks", "page_id", "page_id TEXT NOT NULL DEFAULT 'default'")
    _add_column("rundowns", "page_id", "page_id TEXT NOT NULL DEFAULT 'default'")
    _add_column("pages", "emoji", "emoji TEXT NOT NULL DEFAULT '📄'")
    _conn.execute(text("UPDATE pages SET emoji = '🏠' WHERE id = 'default' AND emoji = '📄'"))
    # Ensure the default page exists so existing blocks have a home.
    if not _conn.execute(text("SELECT 1 FROM pages WHERE id = 'default'")).first():
        _conn.execute(
            text("INSERT INTO pages (id, name, created_at) VALUES ('default', 'Home', datetime('now'))")
        )
    _conn.commit()

app = FastAPI(title="latent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(blocks.router)
app.include_router(pages.router)
app.include_router(rundown.router)


@app.get("/health")
def health() -> dict:
    return {"ok": True}
