# latent

A single, streamlined dashboard for everything you need to keep up with — news,
academic papers, YouTube, sports — pulled from the sources *you* connect and laid
out as adaptable content blocks.

## Idea

- **Adaptable blocks UI.** You choose what shows up. Add, move, and resize blocks;
  each block is a feed from a source you care about.
- **Bring your own sources.** Connect your Google account (YouTube + Gmail in one
  step) and the app knows where to pull from.
- **A consolidated rundown.** Instead of ten tabs, one view that summarizes what's
  new and worth your attention.

## Stack

| Layer     | Choice |
|-----------|--------|
| Frontend  | React + Vite + TypeScript + Tailwind + shadcn/ui |
| Blocks    | react-grid-layout (drag/resize) + TanStack Query + zustand |
| Backend   | FastAPI (Python) |
| Agents    | LangGraph multi-agent system (supervisor → workers → critic) |
| Memory    | RAG over your library (vector store) |
| Auth      | Google OAuth — one consent covers YouTube + Gmail |

## Structure

```
frontend/   React app (the dashboard + blocks)
backend/    FastAPI: integrations, agents, RAG, API
  app/integrations/   where content comes FROM (youtube, gmail, …)
  app/agents/         LangGraph multi-agent pipeline
  app/rag/            the "what I already know" memory layer
docs/       design notes
scripts/    dev helpers
```

## Getting started

> Scaffolding in progress. Quickstart (install, env, run) lands with the
> frontend + backend boilerplate.

1. `cp .env.example .env` and fill in values.
2. Frontend: `cd frontend && npm install && npm run dev`
3. Backend: `cd backend && uv sync && uv run uvicorn app.main:app --reload`

## Roadmap

- [x] Project structure
- [ ] Frontend + backend boilerplate (runnable skeleton)
- [ ] Adaptable blocks dashboard UI
- [ ] Google OAuth (YouTube + Gmail)
- [ ] Source connectors → content feeds
- [ ] User email + auth
- [ ] LangGraph agents: summarize + consolidate the rundown
