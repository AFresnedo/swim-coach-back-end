FROM python:3.14-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM python:3.14-slim AS runtime

WORKDIR /app

COPY --from=builder /app/.venv .venv
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini alembic.ini

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
# --forwarded-allow-ips trusts X-Forwarded-For (the real client IP, forwarded
# by the frontend's own server-side BFF layer - see app/rate_limit.py) only
# when it comes from the frontend container's own pinned address on the
# internal Docker network (see ../infra/docker-compose.yml). Any other sender
# reaching this backend has its claimed X-Forwarded-For ignored entirely, so
# this can't be used to spoof a rate-limit key from anywhere else.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=172.28.0.10"]
