from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import Response

from app.auth.router import router as auth_router
from app.config import Settings, settings
from app.database import check_connection
from app.docs import docs_urls
from app.goal.router import router as goal_router
from app.profile.router import router as profile_router
from app.rag.router import router as training_router
from app.rate_limit import check_storage
from app.stats.router import router as stats_router
from app.swim_time.router import router as swim_time_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    check_connection()
    check_storage()
    yield


def create_app(settings: Settings = settings) -> FastAPI:
    docs = docs_urls(settings.environment)

    app = FastAPI(
        title="SwimCoach API",
        docs_url=docs.docs_url,
        redoc_url=docs.redoc_url,
        openapi_url=docs.openapi_url,
        lifespan=lifespan,
    )

    # "backend" is Docker Compose's DNS name for this service (see
    # ../infra/docker-compose.yml) - the only Host header a legitimate production
    # request ever carries, since it's the sole address the frontend's own
    # outbound fetch() call ever targets. "testserver" is FastAPI TestClient's
    # default Host (this test suite depends on it); "localhost"/"127.0.0.1" cover
    # a plain local `uvicorn --reload` run. Hardcoded rather than settings-driven,
    # same as the Dockerfile's --forwarded-allow-ips: this is a structural fact
    # about our deployment topology, not a per-deployment tunable - keep it in
    # sync here if that topology ever changes. Doesn't stop a request already
    # inside the Docker network from simply setting Host: backend itself - this
    # only guards against traffic reaching this process some other way than the
    # one real caller (e.g. a future routing misconfiguration).
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["backend", "testserver", "localhost", "127.0.0.1"],
    )

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # Tells the browser to trust our Content-Type instead of guessing one from
        # the response body ("MIME-sniffing") - closes a low-likelihood XSS class
        # for free, since we never serve user-controlled content that could be
        # crafted to look like HTML/JS under a different declared type.
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    app.include_router(auth_router)
    app.include_router(goal_router)
    app.include_router(profile_router)
    app.include_router(stats_router)
    app.include_router(swim_time_router)
    app.include_router(training_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
