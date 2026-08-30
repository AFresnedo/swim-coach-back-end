"""Spike for the proposed "Personalized plans" front-end feature: proves out
whether Claude reliably returns a week-by-week TrainingPlan shape (weeks ->
sessions -> sets) via a forced tool call, before the front end commits to that
schema or a backend endpoint gets built around it.

No DB, no existing /training pipeline code touched - this calls
anthropic_client directly with a candidate tool schema, the same way
scripts/spike_citations_ingestion_direct.py proved out web-fallback citations
before app/rag/web_fallback.py was written against real API behavior.

    uv run python -m scripts.spike_structured_plan_output

Requires ANTHROPIC_API_KEY (see .env) - this makes a real, billed API call.
Prints the raw structured output plus a flattened human-readable rendering
you'd actually see in a plan UI, so both the JSON shape and its content
quality can be eyeballed at once.
"""

import json
from pathlib import Path
from typing import Any

from anthropic.types import ToolParam

from app.config import settings
from app.rag.clients import anthropic_client

OUTPUT_PATH = Path(__file__).parent / "spike_structured_plan_output_result.json"

_TOOL_NAME = "submit_training_plan"

_REQUESTED_WEEKS = 3
_REQUESTED_SESSIONS_PER_WEEK = 4


def _nullable_int() -> dict[str, Any]:
    return {"anyOf": [{"type": "integer"}, {"type": "null"}]}


_SUBMIT_PLAN_TOOL: ToolParam = {
    "name": _TOOL_NAME,
    "description": "Submit the generated week-by-week training plan.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "weeks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "week_number": {"type": "integer"},
                        "sessions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "focus": {"type": "string"},
                                    "sets": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "description": {"type": "string"},
                                                "distance_meters": _nullable_int(),
                                                "reps": _nullable_int(),
                                                "rest_seconds": _nullable_int(),
                                            },
                                            "required": [
                                                "description",
                                                "distance_meters",
                                                "reps",
                                                "rest_seconds",
                                            ],
                                            "additionalProperties": False,
                                        },
                                    },
                                },
                                "required": ["focus", "sets"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["week_number", "sessions"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["summary", "weeks"],
        "additionalProperties": False,
    },
}

_SYSTEM_PROMPT = f"""You are a swim coach assistant generating a personalized, week-by-week \
training plan. Fill out the submit_training_plan tool with a realistic plan matching the \
swimmer's request below - do not answer in prose, only call the tool.

Swimmer: 16yo, intermediate freestyle swimmer.
Active goal: Break 1:00 in the 100m freestyle by the end of the season.
Requested plan length: {_REQUESTED_WEEKS} weeks, {_REQUESTED_SESSIONS_PER_WEEK} sessions per week."""


def main() -> None:
    response = anthropic_client.messages.create(
        model=settings.coach_model,
        max_tokens=4000,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": "Generate my plan."}],
        tools=[_SUBMIT_PLAN_TOOL],
        tool_choice={"type": "tool", "name": _TOOL_NAME},
    )

    print(f"stop_reason: {response.stop_reason}\n")
    tool_use = next((block for block in response.content if block.type == "tool_use"), None)
    if tool_use is None:
        print("No tool_use block returned.")
        return

    plan = tool_use.input
    OUTPUT_PATH.write_text(json.dumps(plan, indent=2))
    print(f"Raw output written to {OUTPUT_PATH}\n")

    print(f"Summary: {plan.get('summary')}\n")
    weeks = plan.get("weeks", [])
    print(f"Weeks returned: {len(weeks)} (requested {_REQUESTED_WEEKS})")
    for week in weeks:
        sessions = week.get("sessions", [])
        print(f"\nWeek {week.get('week_number')} - {len(sessions)} session(s) (requested {_REQUESTED_SESSIONS_PER_WEEK})")
        for session in sessions:
            print(f"  Focus: {session.get('focus')}")
            for s in session.get("sets", []):
                print(
                    f"    - {s.get('description')} "
                    f"(distance_m={s.get('distance_meters')}, reps={s.get('reps')}, "
                    f"rest_s={s.get('rest_seconds')})"
                )


if __name__ == "__main__":
    main()
