from typing import Literal, get_args

SexLiteral = Literal["male", "female", "prefer_not_to_say"]
UnitPreferenceLiteral = Literal["metric", "imperial"]

SEXES: tuple[str, ...] = get_args(SexLiteral)
UNIT_PREFERENCES: tuple[str, ...] = get_args(UnitPreferenceLiteral)
