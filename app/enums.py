from typing import Literal, get_args

StrokeLiteral = Literal["freestyle", "backstroke", "breaststroke", "butterfly", "individual_medley"]
CourseLiteral = Literal["scy", "scm", "lcm"]

STROKES: tuple[str, ...] = get_args(StrokeLiteral)
COURSES: tuple[str, ...] = get_args(CourseLiteral)
