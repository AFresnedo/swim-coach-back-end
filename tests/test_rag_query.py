import pytest

from app.rag.query import clean_question


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("how do i improve my flip turns?", "how do i improve my flip turns?"),
        ("  leading and trailing spaces  ", "leading and trailing spaces"),
        ("multiple    internal     spaces", "multiple internal spaces"),
        ("line one\nline two\n\nline three", "line one line two line three"),
        ("tabs\tand\nnewlines\tmixed", "tabs and newlines mixed"),
        ("", ""),
        ("   ", ""),
    ],
)
def test_clean_question(raw, expected):
    assert clean_question(raw) == expected
