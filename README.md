# SwimCoach API

[![CI](https://github.com/AFresnedo/swim-coach-back-end/actions/workflows/ci.yml/badge.svg)](https://github.com/AFresnedo/swim-coach-back-end/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-All%20Rights%20Reserved-red)](LICENSE)

FastAPI backend for [SwimCoach](https://swim-coach-ai.com), a website for personalized,
AI-assisted swim instruction. Handles auth, profiles, goals, swim logs, and a hybrid
RAG training-coach endpoint for the [swim-coach](../swim-coach) Next.js frontend, which
talks to this API through its own BFF proxy layer rather than calling it directly.

Sibling repos: [front-end](https://github.com/AFresnedo/swim-coach-front-end) ·
[infra](https://github.com/AFresnedo/swim-coach-infra) (shared docker-compose, deploy target)

## Stack

Python 3.14 · FastAPI · PostgreSQL (+ pgvector) · SQLAlchemy · Alembic · Redis ·
JWT / bcrypt · Ruff · Pyright · Bandit · pip-audit · pytest

## Setup

```bash
uv sync
cp .env.example .env  # then edit SECRET_KEY (see Environment variables below)
ln -sf ../../scripts/hooks/post-merge .git/hooks/post-merge  # auto-runs pending migrations after pull/merge
docker compose up -d  # starts local Postgres (with pgvector) + Redis (see docker-compose.yml)
uv run alembic upgrade head
```

## Run

```bash
uv run uvicorn app.main:app --reload --port 8000
```

The frontend expects this API at `http://localhost:8000` (see `swim-coach/.env.local`).
Interactive API docs (Swagger UI / ReDoc) are available at `/docs` and `/redoc` while
`ENVIRONMENT=development` — both are disabled when running as `production`.

## Environment variables

All variables are documented in [`.env.example`](.env.example); the notable ones:

| Variable | Default | Notes |
| --- | --- | --- |
| `ENVIRONMENT` | `development` | `production` disables `/docs`, `/redoc`, `/openapi.json` |
| `DATABASE_URL` | `sqlite:///./swimcoach.db` | local dev/CI point this at Postgres via `docker-compose.yml` |
| `SECRET_KEY` | *(required)* | JWT signing key (HS256) — no default, fails fast at startup if unset |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | JWT expiry |
| `REDIS_URL` | `memory://` | in-process store; set to a real Redis URL outside tests |
| `LOGIN_RATE_LIMIT_PER_EMAIL` / `_PER_IP` | `5/5minutes` / `20/5minutes` | see `app/rate_limit.py` |
| `REGISTER_RATE_LIMIT_PER_IP` | `5/hour` | |
| `STATS_RATE_LIMIT_PER_IP` | `30/minute` | |
| `ANTHROPIC_API_KEY` | *(required)* | powers the `/training/ask` coach answer |
| `VOYAGE_API_KEY` | *(required)* | question/knowledge-base embeddings |
| `COACH_MODEL` | `claude-sonnet-5` | or `claude-haiku-4-5` |
| `SIMILARITY_THRESHOLD` | `0.75` | minimum cosine similarity counted as a KB hit |
| `MAX_WEB_INGESTIONS_PER_QUERY` | `2` | ingestion guardrail for the (in-progress) web-search fallback |
| `SHARPEN_MODEL` | `claude-haiku-4-5` | miss-rescue question rewrite, see below |

The `/training/ask` miss-rescue step (rewriting a question using the swimmer's profile
and goals when retrieval misses) is toggled independently of any env var — it reads a
Redis key at request time so it can be flipped without a restart:

```bash
redis-cli SET training:sharpen_enabled 1   # or 0 to disable
```

## API

- `POST /auth/register` — `{name, email, password}` → `{access_token, token_type}`
- `POST /auth/login` — `{email, password}` → `{access_token, token_type}`
- `GET /auth/me` — requires `Authorization: Bearer <token>`, returns the current user
- `POST /auth/logout` — revokes the current token
- `GET /profile` / `PUT /profile` — the current user's profile
- `GET /goals` / `POST /goals` — list / create goals
- `PATCH /goals/{goal_id}` / `PATCH /goals/{goal_id}/deactivate`
- `GET /swim-times` / `POST /swim-times` — paginated swim log
- `GET /stats/users-count` / `GET /stats/swims-count` — public landing-page counters
- `POST /training/ask` — `{question}` → a hybrid-RAG coaching answer grounded in the
  swimmer's goals and a swim-knowledge base (see [design doc](https://trello.com/c/kRedTWbB/91-hybrid-rag-training-coach-endpoint-web-search-fallback-v2) —
  the web-search fallback that grows the KB is still in progress)
- `GET /health`

The list above is a quick reference; `/docs` always reflects the live schema.

## Auth

Passwords are hashed with bcrypt. Auth uses stateless JWTs (HS256) signed with
`SECRET_KEY`, sent as `Authorization: Bearer <token>` and validated in `app/deps.py`.
Logout revokes the token on the backend rather than relying solely on the client
discarding it.

## Development

Install dev dependencies (linting, type checking, tests) on top of the runtime ones:

```bash
uv sync
```

Before pushing, you can run every check CI runs, in the same order, to catch failures locally:

```bash
uv run ruff format --check .                            # formatting
uv run ruff check .                                     # lint
uv run pyright .                                        # type check
uv run bandit -r app -x "*/*_test.py,app/conftest.py"   # security static analysis
uv run pytest -v                                        # tests + coverage report
```

`uv run ruff format .` (no `--check`) will auto-fix formatting in place.

## Continuous Integration & pull requests

`main` is a protected branch — there is no direct push access, including for repo admins.
All changes go through a pull request. The workflow:

```bash
git checkout -b my-change
# ... commit your changes ...
git push -u origin my-change
gh pr create --fill
gh pr merge --auto --squash   # merges automatically once CI passes
```

A PR can be merged as soon as CI passes — no approving review is required (this is a
solo/small-team project), but the `test` check below is a hard requirement. Merges are
always squashed into a single commit, and the source branch is deleted automatically.

Every PR and every push to `main` runs [`.github/workflows/ci.yml`](.github/workflows/ci.yml),
which mirrors the local commands above plus a dependency vulnerability scan:

1. `uv sync --locked` — install dependencies, fails if `uv.lock` is out of sync with `pyproject.toml`
2. `ruff format --check` — formatting
3. `ruff check` — lint
4. `pyright` — type checking
5. `bandit -r app -x "*/*_test.py,app/conftest.py"` — security static analysis (tests are
   colocated inside `app/`, so they're excluded here rather than living outside its scan)
6. `pip-audit` (via `uvx`, against an exported `uv.lock`) — known CVEs in dependencies
7. `pytest -v` — tests, with coverage reported (currently ~99%)

It also spins up a live Postgres service container to verify Alembic migrations apply
cleanly from scratch. The job times out after 10 minutes and runs with read-only repo
permissions. Pushing again to the same branch cancels any still-running run for that
branch, so only the latest matters.

On every push to `main`, [`.github/workflows/cd.yml`](.github/workflows/cd.yml) builds and
pushes a Docker image to GHCR, then deploys over SSH to the production Droplet, running
Alembic migrations before restarting the service and finishing with a smoke test against
`/health`.

[Dependabot](.github/dependabot.yml) opens PRs weekly for outdated Python dependencies and
outdated GitHub Actions versions; they go through the same CI gate as any other PR.

## License

All rights reserved — see [LICENSE](LICENSE). This repo is public for reference and
portfolio purposes only; no permission is granted to use, copy, modify, or distribute
this code, and it isn't open to outside contributions.
