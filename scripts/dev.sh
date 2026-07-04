#!/usr/bin/env bash
# Run latent: backend (:8000) + frontend (:5173) in one go. Ctrl+C stops both.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── prereqs ──────────────────────────────────────────
command -v uv >/dev/null || { echo "✗ uv not found (https://docs.astral.sh/uv)"; exit 1; }
command -v pnpm >/dev/null || { echo "✗ pnpm not found (npm i -g pnpm)"; exit 1; }
command -v claude >/dev/null \
  && echo "✓ claude CLI found — agents run on your subscription" \
  || echo "⚠ claude CLI not found — agents fall back to ANTHROPIC_API_KEY or regex"

[ -f "$ROOT/.env" ] || { cp "$ROOT/.env.example" "$ROOT/.env"; echo "✓ created .env from .env.example (fill in Google OAuth creds)"; }
[ -f "$ROOT/frontend/.env" ] || printf 'VITE_API_BASE_URL=http://localhost:8000\nVITE_USE_MOCK=false\n' > "$ROOT/frontend/.env"

# ── install deps if missing ──────────────────────────
[ -d "$ROOT/frontend/node_modules" ] || (cd "$ROOT/frontend" && pnpm install)
[ -d "$ROOT/backend/.venv" ] || (cd "$ROOT/backend" && uv sync)

# ── run both, die together ───────────────────────────
cleanup() { echo; echo "stopping…"; kill 0 2>/dev/null; }
trap cleanup INT TERM

(cd "$ROOT/backend" && uv run uvicorn app.main:app --reload --port 8000) &
(cd "$ROOT/frontend" && pnpm dev) &

echo
echo "  backend  → http://localhost:8000"
echo "  frontend → http://localhost:5173"
echo "  Ctrl+C to stop both"
echo
wait
