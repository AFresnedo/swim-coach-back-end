from app.config import settings
from app.main import create_app


def _docs_urls(environment: str | None) -> tuple[str | None, str | None, str | None]:
    app_settings = settings if environment is None else settings.model_copy(update={"environment": environment})
    app = create_app(app_settings)
    return app.docs_url, app.redoc_url, app.openapi_url


def test_docs_enabled_by_default():
    assert _docs_urls(None) == ("/docs", "/redoc", "/openapi.json")


def test_docs_enabled_in_development():
    assert _docs_urls("development") == ("/docs", "/redoc", "/openapi.json")


def test_docs_disabled_in_production():
    assert _docs_urls("production") == (None, None, None)


def test_trusted_host_allows_backend(client):
    response = client.get("/health", headers={"Host": "backend"})
    assert response.status_code == 200


def test_trusted_host_rejects_unknown_host(client):
    response = client.get("/health", headers={"Host": "evil.example.com"})
    assert response.status_code == 400


def test_nosniff_header_present(client):
    response = client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
