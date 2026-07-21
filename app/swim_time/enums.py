from typing import Literal, get_args

CourseLiteral = Literal["scy", "scm", "lcm"]

COURSES: tuple[str, ...] = get_args(CourseLiteral)
