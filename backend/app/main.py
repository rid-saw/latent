from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, blocks, rundown
from app.config import settings
from app.db import models  # noqa: F401 — register tables
from app.db.database import Base, engine

Base.metadata.create_all(engine)

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
