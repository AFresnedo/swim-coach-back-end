import base64
from unittest.mock import MagicMock, patch

from app.config import settings
from app.goal.model import Goal
from app.profile.model import Profile
from app.rag.models import ALLOWED_WEB_DOMAINS
from app.rag.swimmer_context import SwimmerContext
from app.rag.web_fallback import CitedSource, answer_with_web_fallback

_NO_SWIMMER = SwimmerContext(profile=None, goals=[])

# A minimal hand-built single-page PDF containing the text "Hello World" -
# enough to exercise a real pdfminer parse without depending on a fixture file.
_VALID_PDF_BYTES = b"""%PDF-1.4
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


def _text_block(text: str, citations: list | None = None) -> MagicMock:
    return MagicMock(type="text", text=text, citations=citations)


def _fetch_block(url: str, text: str, *, source_type: str = "text") -> MagicMock:
    source = MagicMock(type=source_type, data=text)
    fetch_content = MagicMock(type="web_fetch_result", url=url, content=MagicMock(source=source))
    return MagicMock(type="web_fetch_tool_result", content=fetch_content)


def _pdf_fetch_block(url: str, pdf_bytes: bytes) -> MagicMock:
    source = MagicMock(type="base64", media_type="application/pdf", data=base64.b64encode(pdf_bytes).decode())
    fetch_content = MagicMock(type="web_fetch_result", url=url, content=MagicMock(source=source))
    return MagicMock(type="web_fetch_tool_result", content=fetch_content)


def _char_citation(document_index: int) -> MagicMock:
    return MagicMock(type="char_location", document_index=document_index)


def _search_result_citation(url: str) -> MagicMock:
    return MagicMock(type="web_search_result_location", url=url)


def _submit_candidates_block(candidates: list[dict]) -> MagicMock:
    # MagicMock(name=...) sets the mock's internal debug name, not a real
    # .name attribute - it must be assigned after construction instead.
    block = MagicMock(type="tool_use", input={"candidates": candidates})
    block.name = "submit_ingestion_candidates"
    return block


def _stream_returning(response: MagicMock) -> MagicMock:
    fake_stream = MagicMock()
    fake_stream.__enter__.return_value.get_final_message.return_value = response
    return fake_stream


def _stream_sequence(*responses: MagicMock) -> list[MagicMock]:
    """side_effect for anthropic_client.messages.stream across a first call
    plus a tool_use continuation - one fake stream per turn, in call order."""
    return [_stream_returning(response) for response in responses]


_CANDIDATE = {
    "source_url": "https://swimswam.com/catch",
    "quality_score": 0.8,
    "quality_flag": "pass",
    "quality_reason": "Clear coaching advice.",
    "stroke_type": "freestyle",
    "topic_category": "technique",
    "skill_level": "intermediate",
}


def test_answer_with_web_fallback_reconstructs_answer_and_sources():
    # Realistic shape per the confirming spike: the model fetches and calls
    # submit_ingestion_candidates before writing anything to the swimmer -
    # turn 1 has no text blocks at all, and the citation-bearing answer only
    # shows up in the continuation after a tool_result is sent back. The
    # continuation's char_location(0) must still resolve against turn 1's
    # fetch, proving citations correctly resolve across the two turns.
    turn1 = MagicMock(
        content=[
            _fetch_block("https://swimswam.com/catch", "Full page text about the catch."),
            _submit_candidates_block([_CANDIDATE]),
        ],
        stop_reason="tool_use",
    )
    turn2 = MagicMock(
        content=[
            _text_block("Try a high-elbow catch. "),
            _text_block("Keep the elbow up.", citations=[_char_citation(0)]),
        ],
        stop_reason="end_turn",
    )

    with patch("app.rag.web_fallback.anthropic_client.messages.stream", side_effect=_stream_sequence(turn1, turn2)):
        result = answer_with_web_fallback("how do I improve my catch?", swimmer=_NO_SWIMMER)

    assert result.answer == "Try a high-elbow catch. Keep the elbow up."
    assert result.sources == [CitedSource(url="https://swimswam.com/catch", fetched=True)]


def test_answer_with_web_fallback_pairs_candidates_with_fetched_text():
    turn1 = MagicMock(
        content=[
            _fetch_block("https://swimswam.com/catch", "Full page text about the catch."),
            _submit_candidates_block([_CANDIDATE]),
        ],
        stop_reason="tool_use",
    )
    turn2 = MagicMock(content=[_text_block("Answer.")], stop_reason="end_turn")

    with patch("app.rag.web_fallback.anthropic_client.messages.stream", side_effect=_stream_sequence(turn1, turn2)):
        result = answer_with_web_fallback("how do I improve my catch?", swimmer=_NO_SWIMMER)

    assert len(result.fetched_pages) == 1
    page = result.fetched_pages[0]
    assert page.source_url == "https://swimswam.com/catch"
    assert page.raw_text == "Full page text about the catch."
    assert page.quality_flag == "pass"
    assert page.stroke_type == "freestyle"
    assert page.topic_category == "technique"
    assert page.skill_level == "intermediate"


def test_answer_with_web_fallback_continues_past_tool_use_with_no_answer_yet():
    # The exact failure the spike caught: turn 1 stops on tool_use with zero
    # text blocks written. Without the continuation, this would silently
    # produce an empty answer instead of erroring or retrying.
    turn1 = MagicMock(
        content=[
            _fetch_block("https://swimswam.com/catch", "Full page text about the catch."),
            _submit_candidates_block([_CANDIDATE]),
        ],
        stop_reason="tool_use",
    )
    turn2 = MagicMock(content=[_text_block("Try a high-elbow catch.")], stop_reason="end_turn")

    with patch(
        "app.rag.web_fallback.anthropic_client.messages.stream", side_effect=_stream_sequence(turn1, turn2)
    ) as mock_stream:
        result = answer_with_web_fallback("how do I improve my catch?", swimmer=_NO_SWIMMER)

    assert result.answer == "Try a high-elbow catch."
    assert mock_stream.call_count == 2

    second_call_messages = mock_stream.call_args_list[1].kwargs["messages"]
    assert second_call_messages[0] == {"role": "user", "content": "how do I improve my catch?"}
    assert second_call_messages[1] == {"role": "assistant", "content": turn1.content}
    tool_result_message = second_call_messages[2]
    assert tool_result_message["role"] == "user"
    assert tool_result_message["content"] == [
        {
            "type": "tool_result",
            "tool_use_id": turn1.content[1].id,
            "content": "Candidates recorded.",
        }
    ]


def test_answer_with_web_fallback_skips_continuation_when_turn_ends_without_tool_use():
    response = MagicMock(content=[_text_block("Answer with no fetch backing it.")], stop_reason="end_turn")

    with patch(
        "app.rag.web_fallback.anthropic_client.messages.stream", return_value=_stream_returning(response)
    ) as mock_stream:
        result = answer_with_web_fallback("question", swimmer=_NO_SWIMMER)

    assert result.answer == "Answer with no fetch backing it."
    assert mock_stream.call_count == 1


def test_answer_with_web_fallback_resolves_char_citation_after_a_pdf_fetch():
    # The PDF fetch still occupies a document_index slot even though its text
    # isn't in document_urls's text-only sibling map - the char_location
    # citation below (index 1) must resolve to the *second* fetched document,
    # not skip over the PDF and land on the wrong URL.
    content = [
        _pdf_fetch_block("https://swimswam.com/paper.pdf", _VALID_PDF_BYTES),
        _fetch_block("https://swimswam.com/catch", "Full page text about the catch."),
        _text_block("Keep the elbow up.", citations=[_char_citation(1)]),
    ]
    response = MagicMock(content=content, stop_reason="end_turn")

    with patch("app.rag.web_fallback.anthropic_client.messages.stream", return_value=_stream_returning(response)):
        result = answer_with_web_fallback("how do I improve my catch?", swimmer=_NO_SWIMMER)

    assert result.sources == [CitedSource(url="https://swimswam.com/catch", fetched=True)]


def test_answer_with_web_fallback_collects_search_snippet_citations_too():
    content = [
        _text_block("Answer citing a search snippet directly."),
        _text_block("More text.", citations=[_search_result_citation("https://swimmingworldmagazine.com/tip")]),
    ]
    response = MagicMock(content=content, stop_reason="end_turn")

    with patch("app.rag.web_fallback.anthropic_client.messages.stream", return_value=_stream_returning(response)):
        result = answer_with_web_fallback("question", swimmer=_NO_SWIMMER)

    assert result.sources == [CitedSource(url="https://swimmingworldmagazine.com/tip", fetched=False)]


def test_answer_with_web_fallback_keeps_fetched_true_when_same_url_also_cited_as_snippet():
    content = [
        _fetch_block("https://swimswam.com/catch", "Full page text about the catch."),
        _text_block("Try a high-elbow catch.", citations=[_char_citation(0)]),
        _text_block(" Also covered elsewhere.", citations=[_search_result_citation("https://swimswam.com/catch")]),
    ]
    response = MagicMock(content=content, stop_reason="end_turn")

    with patch("app.rag.web_fallback.anthropic_client.messages.stream", return_value=_stream_returning(response)):
        result = answer_with_web_fallback("question", swimmer=_NO_SWIMMER)

    assert result.sources == [CitedSource(url="https://swimswam.com/catch", fetched=True)]


def test_answer_with_web_fallback_reports_mixed_fetched_and_snippet_sources():
    content = [
        _fetch_block("https://swimswam.com/catch", "Full page text about the catch."),
        _text_block("Try a high-elbow catch.", citations=[_char_citation(0)]),
        _text_block(
            " Also see this tip.", citations=[_search_result_citation("https://swimmingworldmagazine.com/tip")]
        ),
    ]
    response = MagicMock(content=content, stop_reason="end_turn")

    with patch("app.rag.web_fallback.anthropic_client.messages.stream", return_value=_stream_returning(response)):
        result = answer_with_web_fallback("question", swimmer=_NO_SWIMMER)

    assert result.sources == [
        CitedSource(url="https://swimswam.com/catch", fetched=True),
        CitedSource(url="https://swimmingworldmagazine.com/tip", fetched=False),
    ]


def test_answer_with_web_fallback_drops_candidate_with_no_matching_fetch():
    hallucinated_candidate = {**_CANDIDATE, "source_url": "https://swimswam.com/never-fetched"}
    turn1 = MagicMock(content=[_submit_candidates_block([hallucinated_candidate])], stop_reason="tool_use")
    turn2 = MagicMock(content=[_text_block("Answer with no fetch backing it.")], stop_reason="end_turn")

    with patch("app.rag.web_fallback.anthropic_client.messages.stream", side_effect=_stream_sequence(turn1, turn2)):
        result = answer_with_web_fallback("question", swimmer=_NO_SWIMMER)

    assert result.fetched_pages == []


def test_answer_with_web_fallback_skips_pdf_fetch_when_extraction_disabled():
    # pdf_extraction_enabled defaults to False - not patched here on purpose,
    # to prove the code path shipped before PDF support even exists in this
    # default state (see _fetched_text_by_url).
    assert settings.pdf_extraction_enabled is False
    pdf_candidate = {**_CANDIDATE, "source_url": "https://swimswam.com/paper.pdf"}
    turn1 = MagicMock(
        content=[
            _pdf_fetch_block("https://swimswam.com/paper.pdf", _VALID_PDF_BYTES),
            _submit_candidates_block([pdf_candidate]),
        ],
        stop_reason="tool_use",
    )
    turn2 = MagicMock(content=[_text_block("Answer.")], stop_reason="end_turn")

    with patch("app.rag.web_fallback.anthropic_client.messages.stream", side_effect=_stream_sequence(turn1, turn2)):
        result = answer_with_web_fallback("question", swimmer=_NO_SWIMMER)

    assert result.fetched_pages == []
    assert result.sources == []


def test_answer_with_web_fallback_extracts_pdf_text_when_extraction_enabled(monkeypatch):
    monkeypatch.setattr(settings, "pdf_extraction_enabled", True)
    pdf_candidate = {**_CANDIDATE, "source_url": "https://swimswam.com/paper.pdf"}
    turn1 = MagicMock(
        content=[
            _pdf_fetch_block("https://swimswam.com/paper.pdf", _VALID_PDF_BYTES),
            _submit_candidates_block([pdf_candidate]),
        ],
        stop_reason="tool_use",
    )
    turn2 = MagicMock(content=[_text_block("Answer.")], stop_reason="end_turn")

    with patch("app.rag.web_fallback.anthropic_client.messages.stream", side_effect=_stream_sequence(turn1, turn2)):
        result = answer_with_web_fallback("question", swimmer=_NO_SWIMMER)

    assert len(result.fetched_pages) == 1
    page = result.fetched_pages[0]
    assert page.source_url == "https://swimswam.com/paper.pdf"
    assert "Hello World" in page.raw_text


def test_answer_with_web_fallback_drops_pdf_candidate_when_extraction_fails(monkeypatch):
    monkeypatch.setattr(settings, "pdf_extraction_enabled", True)
    pdf_candidate = {**_CANDIDATE, "source_url": "https://swimswam.com/corrupt.pdf"}
    turn1 = MagicMock(
        content=[
            _pdf_fetch_block("https://swimswam.com/corrupt.pdf", b"not a real pdf"),
            _submit_candidates_block([pdf_candidate]),
        ],
        stop_reason="tool_use",
    )
    turn2 = MagicMock(content=[_text_block("Answer.")], stop_reason="end_turn")

    with patch("app.rag.web_fallback.anthropic_client.messages.stream", side_effect=_stream_sequence(turn1, turn2)):
        result = answer_with_web_fallback("question", swimmer=_NO_SWIMMER)

    assert result.fetched_pages == []


def test_answer_with_web_fallback_builds_tool_definitions_with_domain_and_caller_restrictions():
    response = MagicMock(content=[_text_block("Answer.")])

    with patch(
        "app.rag.web_fallback.anthropic_client.messages.stream", return_value=_stream_returning(response)
    ) as mock_stream:
        answer_with_web_fallback("question", swimmer=_NO_SWIMMER)

    tools = mock_stream.call_args.kwargs["tools"]
    web_search_tool = next(tool for tool in tools if tool["name"] == "web_search")
    web_fetch_tool = next(tool for tool in tools if tool["name"] == "web_fetch")

    assert web_search_tool["allowed_domains"] == list(ALLOWED_WEB_DOMAINS)
    assert web_search_tool["allowed_callers"] == ["direct"]
    assert web_fetch_tool["allowed_domains"] == list(ALLOWED_WEB_DOMAINS)
    assert web_fetch_tool["allowed_callers"] == ["direct"]
    assert web_fetch_tool["citations"] == {"enabled": True}


def test_answer_with_web_fallback_system_prompt_tells_model_to_disregard_comments():
    response = MagicMock(content=[_text_block("Answer.")])

    with patch(
        "app.rag.web_fallback.anthropic_client.messages.stream", return_value=_stream_returning(response)
    ) as mock_stream:
        answer_with_web_fallback("question", swimmer=_NO_SWIMMER)

    assert "disregard reader comments" in mock_stream.call_args.kwargs["system"]


def test_answer_with_web_fallback_includes_swimmer_context():
    response = MagicMock(content=[_text_block("Answer.")])
    profile = Profile(user_id=1, age=15, height_cm=170.0, weight_kg=60.0, sex="female", unit_preference="metric")
    goals = [Goal(user_id=1, text="sub-60 100 free", is_active=True)]
    swimmer = SwimmerContext(profile=profile, goals=goals)

    with patch(
        "app.rag.web_fallback.anthropic_client.messages.stream", return_value=_stream_returning(response)
    ) as mock_stream:
        answer_with_web_fallback("question", swimmer=swimmer)

    system = mock_stream.call_args.kwargs["system"]
    assert "15yo female" in system
    assert "sub-60 100 free" in system
