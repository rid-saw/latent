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

    # Dev-only token store (single user). Replaced by DB in the auth phase.
    token_store_path: Path = BACKEND_DIR / ".tokens.json"


settings = Settings()
