
## One-time setup (only needed once, or whenever .env is missing)

backend needs context_server/.env with a real IDENTITY_SECRET, or it will
refuse to boot (fails closed per Gate 0 fix — see config.py).

cd context_server
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(32))"   # copy the output...
# ...and paste it as IDENTITY_SECRET=<value> in context_server/.env
# (Obsidian keys in .env are optional unless you're using the Obsidian backend)


## backend

cd context_server
.venv\Scripts\activate
python -m app.main

# serves on http://127.0.0.1:27180


## frontend

cd frontend
npm install   # if not already installed
npm run dev

# serves on http://localhost:3000
# talks to the backend via /api proxy (next.config.js) -> http://127.0.0.1:27180
