"""Google OAuth: one consent covers YouTube + Gmail (both readonly)."""

from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from app.config import settings
from app.core.tokens import load_tokens, save_tokens

router = APIRouter(prefix="/api/auth", tags=["auth"])

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
]
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"


@router.get("/status")
async def status() -> dict:
    """Whether Google actually works — not just whether a token file exists.

    Google expires refresh tokens after 7 days while the OAuth app is in
    "Testing", so a stored token is no evidence of a live connection. Checking
    the file alone reported "connected" against month-old dead credentials,
    and the UI then hid the reconnect button the user needed.
    """
    if load_tokens() is None:
        return {"google": False, "reason": "not_connected"}
    try:
        await get_access_token()  # probes, and silently refreshes if it can
    except HTTPException:
        return {"google": False, "reason": "expired"}
    return {"google": True, "reason": "connected"}


@router.get("/google/login")
def google_login() -> RedirectResponse:
    if not settings.google_client_id:
        raise HTTPException(500, "GOOGLE_CLIENT_ID not configured — see docs/oauth-setup.md")
    params = urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",  # get a refresh_token
            "prompt": "consent",
        }
    )
    return RedirectResponse(f"{AUTH_URL}?{params}")


@router.get("/google/callback")
async def google_callback(code: str) -> RedirectResponse:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    if resp.status_code != 200:
        raise HTTPException(502, f"Token exchange failed: {resp.text}")
    save_tokens(resp.json())
    return RedirectResponse(f"{settings.frontend_origin}?connected=google")


async def get_access_token() -> str:
    """Valid access token, refreshing if needed. Raises 401 if not connected."""
    tokens = load_tokens()
    if not tokens:
        raise HTTPException(401, "Google not connected — visit /api/auth/google/login")

    async with httpx.AsyncClient() as client:
        # Cheap validity probe; refresh on failure.
        probe = await client.get(
            "https://www.googleapis.com/oauth2/v1/tokeninfo",
            params={"access_token": tokens["access_token"]},
        )
        if probe.status_code == 200:
            return tokens["access_token"]

        refresh = tokens.get("refresh_token")
        if not refresh:
            raise HTTPException(401, "Token expired and no refresh token — reconnect Google")
        resp = await client.post(
            TOKEN_URL,
            data={
                "refresh_token": refresh,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "grant_type": "refresh_token",
            },
        )
    if resp.status_code != 200:
        raise HTTPException(401, "Token refresh failed — reconnect Google")
    save_tokens(resp.json())
    return load_tokens()["access_token"]
