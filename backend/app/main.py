from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, blocks, rundown
from app.config import settings
from sqlalchemy import text

from app.db import models  # noqa: F401 — register tables
from app.db.database import Base, engine

Base.metadata.create_all(engine)

# Micro-migration: create_all doesn't add columns to existing tables.
with engine.connect() as _conn:
    _cols = [r[1] for r in _conn.execute(text("PRAGMA table_info(blocks)"))]
    if "max_items" not in _cols:
        _conn.execute(text("ALTER TABLE blocks ADD COLUMN max_items INTEGER NOT NULL DEFAULT 5"))
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
app.include_router(rundown.router)


@app.get("/health")
def health() -> dict:
    return {"ok": True}
