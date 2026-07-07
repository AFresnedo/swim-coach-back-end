from fastapi import FastAPI

from app.config import settings
from app.routers import auth, goals, profile, swim_times, users

_docs_enabled = settings.environment != "production"

app = FastAPI(
    title="SwimCoach API",
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)

app.include_router(auth.router)
app.include_router(goals.router)
app.include_router(profile.router)
app.include_router(swim_times.router)
app.include_router(users.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
