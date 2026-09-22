from app.rag.pdf_extract import extract_pdf_text

# A minimal hand-built single-page PDF containing the text "Hello World" -
# enough to exercise a real pdfminer parse without depending on a fixture file.
_VALID_PDF = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 200 200] /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
5 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 20 100 Td (Hello World) Tj ET
endstream
endobj
xref
0 6
0000000000 65535 f
trailer
<< /Size 6 /Root 1 0 R >>
startxref
0
%%EOF
"""


def test_extract_pdf_text_returns_text_from_a_valid_pdf():
    assert extract_pdf_text(_VALID_PDF) is not None
    assert "Hello World" in extract_pdf_text(_VALID_PDF)


def test_extract_pdf_text_returns_none_for_malformed_pdf_bytes():
    assert extract_pdf_text(b"not a pdf at all") is None


def test_extract_pdf_text_returns_none_for_empty_bytes():
    assert extract_pdf_text(b"") is None
