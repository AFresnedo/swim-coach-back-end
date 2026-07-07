from typing import Literal, get_args

StrokeLiteral = Literal["freestyle", "backstroke", "breaststroke", "butterfly", "individual_medley"]
CourseLiteral = Literal["scy", "scm", "lcm"]
SexLiteral = Literal["male", "female", "prefer_not_to_say"]
DeactivationReasonLiteral = Literal["reached", "abandoned", "other"]
UnitPreferenceLiteral = Literal["metric", "imperial"]

STROKES: tuple[str, ...] = get_args(StrokeLiteral)
COURSES: tuple[str, ...] = get_args(CourseLiteral)
SEXES: tuple[str, ...] = get_args(SexLiteral)
DEACTIVATION_REASONS: tuple[str, ...] = get_args(DeactivationReasonLiteral)
UNIT_PREFERENCES: tuple[str, ...] = get_args(UnitPreferenceLiteral)
