"""POC-only: generates a single custom drill via a forced structured tool
call. Temporary demo code for the "Custom drills generator" front-end add-on
- no retrieval/grounding, no persistence. Parameterizes
scripts/spike_structured_drill_output.py, which proved this schema out."""

from typing import Any

from anthropic.types import ToolParam
from pydantic import ValidationError

from app.config import settings
from app.rag.clients import anthropic_client
from app.rag.schema import DrillAskOut

# Same one-retry rationale as app/rag/plan.py.
_MAX_ATTEMPTS = 2

_TOOL_NAME = "submit_generated_drill"


def _nullable_int() -> dict[str, Any]:
    return {"anyOf": [{"type": "integer"}, {"type": "null"}]}


_SUBMIT_DRILL_TOOL: ToolParam = {
    "name": _TOOL_NAME,
    "description": "Submit the generated custom drill.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "motivation": {"type": "string"},
            "benefit": {"type": "string"},
            "steps": {"type": "array", "items": {"type": "string"}},
            "set": {
                "type": "object",
                "properties": {
                    "reps": _nullable_int(),
                    "distance_meters": _nullable_int(),
                    "rest_seconds": _nullable_int(),
                },
                "required": ["reps", "distance_meters", "rest_seconds"],
                "additionalProperties": False,
            },
        },
        "required": ["name", "motivation", "benefit", "steps", "set"],
        "additionalProperties": False,
    },
}

_SYSTEM_PROMPT_TEMPLATE = """You are a swim coach assistant generating one custom drill. Fill \
out the submit_generated_drill tool with a realistic drill matching the request below - do not \
answer in prose, only call the tool. `motivation` should explain, in a sentence or two, why a \
swimmer with this focus/skill level needs this drill specifically. `benefit` should explain, in \
a sentence or two, what improves in their swimming if the drill is performed correctly.

Stroke: {stroke}
Focus area: {focus}
Swimmer skill level: {skill_level}"""


def generate_drill(*, stroke: str, focus: str, skill_level: str) -> DrillAskOut:
    system = _SYSTEM_PROMPT_TEMPLATE.format(stroke=stroke, focus=focus, skill_level=skill_level)

    last_error: Exception = RuntimeError("unreachable")
    for _ in range(_MAX_ATTEMPTS):
        response = anthropic_client.messages.create(
            model=settings.coach_model,
            max_tokens=2000,
            system=system,
            messages=[{"role": "user", "content": "Generate my drill."}],
            tools=[_SUBMIT_DRILL_TOOL],
            tool_choice={"type": "tool", "name": _TOOL_NAME},
        )
        tool_use = next((block for block in response.content if block.type == "tool_use"), None)
        if tool_use is None:
            last_error = RuntimeError(f"No drill returned (stop_reason={response.stop_reason!r})")
            continue
        try:
            return DrillAskOut.model_validate(tool_use.input)
        except ValidationError as err:
            last_error = err
    raise last_error
