# SwimCoach back-end

## FastAPI docs

Before writing or reviewing FastAPI code (path operations, dependencies, streaming, responses, Pydantic integration), check the version-pinned docs shipped inside this project's virtualenv rather than relying on training data, which may be stale or describe a different version:

`.venv/lib/python*/site-packages/fastapi/.agents/skills/fastapi/SKILL.md`

and its `references/` subfolder. These match the exact FastAPI version installed (see `pyproject.toml` / `uv.lock`), which training knowledge cannot guarantee.

## Opinionated workflow preference (personal — delete if you don't agree)

This section reflects one contributor's local working setup, not a team convention. Remove it if it doesn't match your own layout or preferences.

You are an expert back-end programmer who specializes in Python, FastAPI, and SQLAlchemy. The front-end for this project lives at `../swim-coach` and shared infrastructure/deploy config lives at `../infra` — both are sibling checkouts on this machine. You can read, discover, and explore those sister folders, and you may edit `../infra` when a task calls for it (e.g. docker-compose, deploy config). Default to not editing `../swim-coach` — treat it as read-only unless explicitly asked in the conversation to change something there.

If `../swim-coach` or `../infra` aren't present (e.g. a fresh clone, an isolated worktree, or a cloud review run), ignore this section rather than trying to locate them.
