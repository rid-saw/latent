from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]  # repo root
BACKEND_DIR = ROOT / "backend"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    app_env: str = "development"
    backend_port: int = 8000
    frontend_origin: str = "http://localhost:5173"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"

    # LLM agent layer, on whichever AI subscription the user already has.
    # "auto" picks the first installed CLI: claude (Claude sub) -> codex
    # (ChatGPT sub) -> gemini (free Google account) -> ANTHROPIC_API_KEY ->
    # regex fallback.
    llm_backend: str = "auto"  # auto | claude-code | codex | gemini | api | off
    # Routing/critique/summaries are lightweight — a fast model keeps blocks
    # snappy and burns less of the user's usage window. Empty = CLI default.
    llm_model: str = "haiku"  # claude-code backend
    codex_model: str = ""  # codex backend; empty = CLI default
    gemini_model: str = "gemini-2.5-flash"  # gemini backend
    anthropic_api_key: str = ""
    agent_model: str = "claude-haiku-4-5"  # api backend only

    # Dev-only token store (single user). Replaced by DB in the auth phase.
    token_store_path: Path = BACKEND_DIR / ".tokens.json"


settings = Settings()
