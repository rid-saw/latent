# latent

A single, streamlined dashboard for everything you need to keep up with — news,
academic papers, YouTube, sports — pulled from the sources *you* connect and laid
out as adaptable content blocks.

## Idea

- **Adaptable blocks UI.** You choose what shows up. Describe an interest in plain
  English ("latest Fireship videos", "recent papers on AI in medicine"), and an
  agent finds, ranks, and populates a block with it. Drag, resize, rearrange.
- **Bring your own sources.** Connect your Google account (YouTube + Gmail in one
  step). Papers, news, and sports come from open sources — no API keys.
- **Your briefing.** Instead of ten tabs, one agent-written paragraph per page that
  summarizes what's new and worth your attention.
- **Your Claude subscription, not an API bill.** All AI runs headless through the
  Claude Code CLI on the subscription you already have. No API key, no per-token
  charges. (An Anthropic API key works as an optional fallback.)

## Stack

| Layer     | Choice |
|-----------|--------|
| Frontend  | React 19 + Vite + TypeScript + Tailwind v4 |
| Blocks    | react-grid-layout (drag/resize) + zustand |
| Backend   | FastAPI (Python) + SQLite |
| Agents    | LangGraph: supervisor routes → connectors fetch → critic verifies |
| LLM       | **Your Claude subscription** via the Claude Code CLI — no API key needed |
| Auth      | Google OAuth — one consent covers YouTube + Gmail |

## Structure

```
frontend/   React app (the dashboard + blocks)
backend/    FastAPI: integrations, agents, API
  app/integrations/   where content comes FROM (youtube, gmail, papers, news, espn, …)
  app/agents/         LangGraph agent pipeline + briefing
scripts/    dev helpers (scripts/dev.sh runs everything)
```

## Getting started

Prereqs: Node 20+, pnpm, Python 3.12+, uv, and the [Claude Code CLI](https://claude.com/claude-code)
logged in to your Claude subscription.

```sh
./scripts/dev.sh    # starts backend (:8000) + frontend (:5173), Ctrl+C stops both
```

First run: copy `backend/.env.example` → `backend/.env` and add Google OAuth
credentials if you want YouTube/Gmail blocks (everything else works without).

## What works today

- [x] Multi-page dashboard: drag/resize block grid, dark mode, pages with icons
- [x] Natural-language block creation via LangGraph agents (supervisor → fetch → critic)
- [x] Connectors: YouTube, Gmail, papers (OpenAlex/arXiv), Google News, ESPN, pinned sites
- [x] Your briefing: agent-written page summary (one LLM call per briefing)
- [x] Auto-refresh, NEW badges, runs entirely on your Claude subscription
- [ ] Multi-user auth
- [ ] RAG memory ("what I've read") for personalization

## License

[PolyForm Noncommercial 1.0.0](LICENSE.md). You're welcome to clone this, run it,
learn from it, and modify it for personal or research use. Commercial use is not
permitted.

Required Notice: Copyright Riddhi Sawant (https://github.com/rid-saw/latent)
