# SwimCoach back-end

## FastAPI docs

Before writing or reviewing FastAPI code (path operations, dependencies, streaming, responses, Pydantic integration), check the version-pinned docs shipped inside this project's virtualenv rather than relying on training data, which may be stale or describe a different version:

`.venv/lib/python*/site-packages/fastapi/.agents/skills/fastapi/SKILL.md`

and its `references/` subfolder. These match the exact FastAPI version installed (see `pyproject.toml` / `uv.lock`), which training knowledge cannot guarantee.
