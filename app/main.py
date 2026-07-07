from fastapi import FastAPI
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import settings
from app.routers import auth, goals, profile, swim_times, users

_docs_enabled = settings.environment != "production"

app = FastAPI(
    title="SwimCoach API",
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
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

app.include_router(auth.router)
app.include_router(goals.router)
app.include_router(profile.router)
app.include_router(swim_times.router)
app.include_router(users.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
