# SwimCoach API

FastAPI backend for the SwimCoach app. Handles authentication for the
[swim-coach](../swim-coach) Next.js frontend.

## Setup

```bash
uv sync
cp .env.example .env  # then edit SECRET_KEY
```

## Run

```bash
uv run uvicorn app.main:app --reload --port 8000
```

The frontend expects this API at `http://localhost:8000` (see `swim-coach/.env.local`).

## Endpoints

- `POST /auth/register` — `{name, email, password}` -> `{access_token, token_type}`
- `POST /auth/login` — `{email, password}` -> `{access_token, token_type}`
- `GET /auth/me` — requires `Authorization: Bearer <token>`, returns the current user
- `GET /health`

## Auth

Passwords are hashed with bcrypt. Auth uses stateless JWTs (HS256) signed with
`SECRET_KEY`, sent as `Authorization: Bearer <token>` and validated in `app/deps.py`.
