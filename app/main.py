from fastapi import FastAPI

from app.routers import auth, goals, profile, swim_times, users

app = FastAPI(title="SwimCoach API")

app.include_router(auth.router)
app.include_router(goals.router)
app.include_router(profile.router)
app.include_router(swim_times.router)
app.include_router(users.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
