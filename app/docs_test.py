from app.docs import DocsUrls, docs_urls


def test_docs_urls_enabled_for_development():
    assert docs_urls("development") == DocsUrls("/docs", "/redoc", "/openapi.json")


def test_docs_urls_disabled_for_production():
    assert docs_urls("production") == DocsUrls(None, None, None)
