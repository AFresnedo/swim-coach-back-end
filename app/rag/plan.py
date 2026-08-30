"""POC-only: generates a personalized week-by-week training plan via a
forced structured tool call. Temporary demo code for the "Personalized
plans" front-end page - no retrieval/grounding, no persistence. Parameterizes
scripts/spike_structured_plan_output.py, which proved this schema out."""

from typing import Any

from anthropic.types import ToolParam
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import settings
from app.profile.model import Profile
from app.rag.clients import anthropic_client
from app.rag.retrieval import fetch_active_goals
from app.rag.schema import PlanAskOut
from app.rag.swimmer_context import SwimmerContext, build_swimmer_context

# Observed via scripts/verify_poc_plan_drill.py: despite strict:true, the
# model occasionally malforms its own tool input (e.g. dumps the whole plan
# as a string into `summary` instead of populating `weeks`). One retry papers
# over that for demo purposes - not a fix, just enough to keep this POC from
# randomly erroring on stage.
_MAX_ATTEMPTS = 2

_TOOL_NAME = "submit_training_plan"


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

_SYSTEM_PROMPT_TEMPLATE = """You are a swim coach assistant generating a personalized, \
week-by-week training plan. Fill out the submit_training_plan tool with a realistic plan \
matching the swimmer below - do not answer in prose, only call the tool.

Swimmer context:
{swimmer_context}

Requested plan length: {weeks} weeks, {sessions_per_week} sessions per week."""


def generate_plan(db: Session, *, user_id: int, weeks: int, sessions_per_week: int) -> PlanAskOut:
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    goals = fetch_active_goals(db, user_id)
    swimmer = SwimmerContext(profile=profile, goals=goals)

    system = _SYSTEM_PROMPT_TEMPLATE.format(
        swimmer_context=build_swimmer_context(swimmer), weeks=weeks, sessions_per_week=sessions_per_week
    )

    last_error: Exception = RuntimeError("unreachable")
    for _ in range(_MAX_ATTEMPTS):
        response = anthropic_client.messages.create(
            model=settings.coach_model,
            max_tokens=4000,
            system=system,
            messages=[{"role": "user", "content": "Generate my plan."}],
            tools=[_SUBMIT_PLAN_TOOL],
            tool_choice={"type": "tool", "name": _TOOL_NAME},
        )
        tool_use = next((block for block in response.content if block.type == "tool_use"), None)
        if tool_use is None:
            last_error = RuntimeError(f"No plan returned (stop_reason={response.stop_reason!r})")
            continue
        try:
            return PlanAskOut.model_validate(tool_use.input)
        except ValidationError as err:
            last_error = err
    raise last_error
