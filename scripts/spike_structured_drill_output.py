"""Spike for the proposed "Custom drills generator" front-end feature (an
add-on to /strokes/[stroke], logged-in only): proves out whether Claude
reliably returns a single GeneratedDrill shape (name/steps/set) via a forced
tool call, before the front end commits to that schema or a backend endpoint
gets built around it.

No DB, no existing /training pipeline code touched - mirrors
scripts/spike_structured_plan_output.py's approach for the plans schema.

    uv run python -m scripts.spike_structured_drill_output

Requires ANTHROPIC_API_KEY (see .env) - this makes a real, billed API call.
"""

import json
from pathlib import Path
from typing import Any

from anthropic.types import ToolParam

from app.config import settings
from app.rag.clients import anthropic_client

OUTPUT_PATH = Path(__file__).parent / "spike_structured_drill_output_result.json"

_TOOL_NAME = "submit_generated_drill"

_STROKE = "backstroke"
_FOCUS = "technique"
_SKILL_LEVEL = "beginner"


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
        "required": ["name", "steps", "set"],
        "additionalProperties": False,
    },
}

_SYSTEM_PROMPT = f"""You are a swim coach assistant generating one custom drill. Fill out the \
submit_generated_drill tool with a realistic drill matching the request below - do not answer \
in prose, only call the tool.

Stroke: {_STROKE}
Focus area: {_FOCUS}
Swimmer skill level: {_SKILL_LEVEL}"""


def main() -> None:
    response = anthropic_client.messages.create(
        model=settings.coach_model,
        max_tokens=2000,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": "Generate my drill."}],
        tools=[_SUBMIT_DRILL_TOOL],
        tool_choice={"type": "tool", "name": _TOOL_NAME},
    )

    print(f"stop_reason: {response.stop_reason}\n")
    tool_use = next((block for block in response.content if block.type == "tool_use"), None)
    if tool_use is None:
        print("No tool_use block returned.")
        return

    drill = tool_use.input
    OUTPUT_PATH.write_text(json.dumps(drill, indent=2))
    print(f"Raw output written to {OUTPUT_PATH}\n")

    print(f"Name: {drill.get('name')}\n")
    print("Steps:")
    for i, step in enumerate(drill.get("steps", []), start=1):
        print(f"  {i}. {step}")
    s = drill.get("set", {})
    print(
        f"\nSet: reps={s.get('reps')}, distance_m={s.get('distance_meters')}, "
        f"rest_s={s.get('rest_seconds')}"
    )


if __name__ == "__main__":
    main()
