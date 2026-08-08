# Google OAuth setup (one-time, ~5 min)

This is **only for Gmail blocks** — reading your own inbox. Everything else in
latent (papers, YouTube, news, sports, jobs, web search) reads public sources and
needs none of this. Skip this page unless you want your email in there.

## 1. Create the project + enable APIs

1. Go to [console.cloud.google.com](https://console.cloud.google.com/) → create project (e.g. `latent`).
2. **APIs & Services → Library** → enable the **Gmail API**.

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

- Scopes requested: `gmail.readonly`, `userinfo.email` — read-only.
- "Testing" mode refresh tokens expire after 7 days, so you reconnect weekly.
  That's the cost of it staying your own app. Publishing would remove the limit,
  but `gmail.readonly` is a *restricted* scope, so Google requires a paid
  third-party security assessment first — not worth it to read your own mail.
