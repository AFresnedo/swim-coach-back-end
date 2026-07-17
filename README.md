# SwimCoach API

FastAPI backend for the SwimCoach app. Handles authentication for the
[swim-coach](../swim-coach) Next.js frontend.

## Setup

```bash
uv sync
cp .env.example .env  # then edit SECRET_KEY
ln -sf ../../scripts/hooks/post-merge .git/hooks/post-merge  # auto-runs pending migrations after pull/merge
docker compose up -d  # starts local Postgres + Redis (see docker-compose.yml)
uv run alembic upgrade head
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

## Development

Install dev dependencies (linting, type checking, tests) on top of the runtime ones:

```bash
uv sync
```

Before pushing, you can run every check CI runs, in the same order, to catch failures locally:

```bash
uv run ruff format --check .  # formatting
uv run ruff check .           # lint
uv run pyright .               # type check
uv run bandit -r app           # security static analysis
uv run pytest -v               # tests + coverage report
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
5. `bandit -r app` — security static analysis
6. `pip-audit` (via `uvx`, against an exported `uv.lock`) — known CVEs in dependencies
7. `pytest -v` — tests, with coverage reported (currently ~96%)

The job times out after 10 minutes and runs with read-only repo permissions. Pushing again to
the same branch cancels any still-running run for that branch, so only the latest matters.

[Dependabot](.github/dependabot.yml) opens PRs weekly for outdated Python dependencies and
outdated GitHub Actions versions; they go through the same CI gate as any other PR.

## License

All rights reserved — see [LICENSE](LICENSE). This repo is public for reference only;
no permission is granted to use, copy, modify, or distribute this code.
