import subprocess
import sys

# app.main builds its FastAPI() instance once, at import time, from settings
# already resolved at that point - the existing `client`/`app` fixtures share one
# process-wide import, so they can't exercise a different ENVIRONMENT value.
# Each of these spawns a fresh interpreter instead, so the import happens under
# a controlled environment rather than whatever this test process inherited.
_BASE_ENV = {
    "PATH": sys.exec_prefix + "/bin",
    "SECRET_KEY": "test-secret-key-not-real",
    "DATABASE_URL": "sqlite:///:memory:",
}


def _docs_urls(environment: str | None) -> str:
    env = dict(_BASE_ENV)
    if environment is not None:
        env["ENVIRONMENT"] = environment
    script = "from app.main import app; print(app.docs_url, app.redoc_url, app.openapi_url)"
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, env=env, check=True)
    return result.stdout.strip()


def test_docs_enabled_by_default():
    assert _docs_urls(None) == "/docs /redoc /openapi.json"


def test_docs_enabled_in_development():
    assert _docs_urls("development") == "/docs /redoc /openapi.json"


def test_docs_disabled_in_production():
    assert _docs_urls("production") == "None None None"
