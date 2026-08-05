"""/api/auth/status must report whether Google *works*, not whether a file exists.

Regression: status() used to return `load_tokens() is not None`. A month-old
token file with a dead refresh token still reported "connected", so the sidebar
showed a green tick while every YouTube and Gmail block failed — and the UI hid
the reconnect button, leaving no way out.

No network here: get_access_token() is the thing that talks to Google, so it's
stubbed. What's under test is how status() reacts to it.
"""

import json

import pytest
from fastapi import HTTPException

from app.api.routes import auth
from app.config import settings


@pytest.fixture
def token_store(tmp_path, monkeypatch):
    """Point the token store at a temp file, leaving the real one alone."""
    path = tmp_path / "tokens.json"
    monkeypatch.setattr(settings, "token_store_path", path)
    return path


async def test_no_token_file_is_not_connected(token_store):
    assert await auth.status() == {"google": False, "reason": "not_connected"}


async def test_dead_token_reports_expired(token_store, monkeypatch):
    token_store.write_text(json.dumps({"access_token": "x", "refresh_token": "dead"}))

    async def refuse() -> str:
        raise HTTPException(401, "Token refresh failed — reconnect Google")

    monkeypatch.setattr(auth, "get_access_token", refuse)
    assert await auth.status() == {"google": False, "reason": "expired"}


async def test_working_token_reports_connected(token_store, monkeypatch):
    token_store.write_text(json.dumps({"access_token": "x", "refresh_token": "good"}))

    async def succeed() -> str:
        return "fresh-access-token"

    monkeypatch.setattr(auth, "get_access_token", succeed)
    assert await auth.status() == {"google": True, "reason": "connected"}


async def test_missing_tokens_raise_401(token_store):
    """get_access_token bails before any network call when nothing is stored."""
    with pytest.raises(HTTPException) as caught:
        await auth.get_access_token()
    assert caught.value.status_code == 401


