"""PDF text extraction for pages web_fetch returns as a PDF document (see
app/rag/web_fallback.py), gated by RagSettings.pdf_extraction_enabled."""

import io

from pdfminer.high_level import extract_text


def extract_pdf_text(pdf_bytes: bytes) -> str | None:
    """Returns None on any extraction failure rather than raising. The input
    is an arbitrary file fetched from the open web, not something this
    codebase controls the shape of, and pdfminer's failure modes for
    malformed, encrypted, or otherwise unparseable PDFs aren't a small,
    enumerable set of exception types - a bad fetch should be dropped like an
    unmatched candidate, never fail the request that triggered it."""
    try:
        text = extract_text(io.BytesIO(pdf_bytes))
    except Exception:
        return None
    return text or None
