# Google OAuth setup (one-time, ~5 min)

One OAuth client covers **both YouTube and Gmail** — a single consent screen.

## 1. Create the project + enable APIs

1. Go to [console.cloud.google.com](https://console.cloud.google.com/) → create project (e.g. `latent`).
2. **APIs & Services → Library** → enable:
   - **YouTube Data API v3**
   - **Gmail API**

## 2. Consent screen

**APIs & Services → OAuth consent screen**:
- User type: **External**, publishing status **Testing**
- Add yourself under **Test users** (required while in Testing — logins from other accounts fail)

## 3. OAuth client

**APIs & Services → Credentials → Create credentials → OAuth client ID**:
- Type: **Web application**
- Authorized redirect URI: `http://localhost:8000/api/auth/google/callback`

Copy the client ID + secret.

## 4. Configure latent

```bash
cp .env.example .env   # repo root, if not done already
```

Fill in:
```
GOOGLE_CLIENT_ID=<your client id>
GOOGLE_CLIENT_SECRET=<your client secret>
```

## 5. Connect

```bash
cd backend && uv run uvicorn app.main:app --reload   # terminal 1
cd frontend && pnpm dev                               # terminal 2
```

Set `VITE_USE_MOCK=false` in `frontend/.env` (create from `frontend/.env.example`).
Open http://localhost:5173 → **Connect Google** in the sidebar → consent → done.
Tokens land in `backend/.tokens.json` (gitignored, dev-only).

## Notes

- Scopes requested: `youtube.readonly`, `gmail.readonly`, `userinfo.email` — read-only.
- "Testing" mode refresh tokens expire after 7 days — reconnect when that happens
  (fine for dev; publishing the app removes the limit).
