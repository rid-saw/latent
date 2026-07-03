"""Dev-only Google token store: a gitignored JSON file, single user.

Deliberately primitive — replaced by per-user DB rows in the auth phase.
"""

import json

from app.config import settings


def save_tokens(tokens: dict) -> None:
    existing = load_tokens() or {}
    # Google omits refresh_token on re-consent; keep the one we have.
    if "refresh_token" not in tokens and "refresh_token" in existing:
        tokens["refresh_token"] = existing["refresh_token"]
    settings.token_store_path.write_text(json.dumps(tokens, indent=2))


def load_tokens() -> dict | None:
    try:
        return json.loads(settings.token_store_path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None
