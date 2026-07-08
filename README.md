# Agentic OS — runnable starter (Phases 0–2)

## Prerequisites
1. Obsidian running with the **Local REST API with MCP** plugin. Copy the API key from settings.
   HTTPS on https://127.0.0.1:27124 (self-signed cert), HTTP on http://127.0.0.1:27123.
2. Python 3.11+ and Node 18+.

## Setup
    # Backend
    cd context_server
    python -m venv .venv
    # Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env      # paste your OBSIDIAN_REST_API_KEY
    python -m app.main        # http://127.0.0.1:27180

    # Frontend (new terminal)
    cd frontend
    npm install
    npm run dev               # http://127.0.0.1:3000

Open http://127.0.0.1:3000 — green when the Context Server + Obsidian backend are reachable.

## Sanity checks
    curl http://127.0.0.1:27180/health
    curl -X POST http://127.0.0.1:27180/mcp/search_notes \
      -H "X-Agent-Identity: opencode:task-0" -H "Content-Type: application/json" \
      -d '{"query": "hello"}'
