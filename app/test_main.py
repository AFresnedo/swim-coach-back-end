from app.config import settings
from app.docs import docs_urls
from app.main import create_app


def test_create_app_wires_docs_urls_from_settings():
    app = create_app()
    expected = docs_urls(settings.environment)
    assert (app.docs_url, app.redoc_url, app.openapi_url) == (
        expected.docs_url,
        expected.redoc_url,
        expected.openapi_url,
    )


def test_trusted_host_allows_backend(client):
    response = client.get("/health", headers={"Host": "backend"})
    assert response.status_code == 200


def test_trusted_host_rejects_unknown_host(client):
    response = client.get("/health", headers={"Host": "evil.example.com"})
    assert response.status_code == 400


def test_nosniff_header_present(client):
    response = client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
