from typing import Literal, get_args

# Shared across swim_time (a swimmer's own recorded times) and rag (tagging
# SwimKnowledge chunks by stroke) - the one enum genuinely owned by more than
# one domain, so it stays here rather than moving into either domain's own
# enums.py.
StrokeLiteral = Literal["freestyle", "backstroke", "breaststroke", "butterfly", "individual_medley"]

STROKES: tuple[str, ...] = get_args(StrokeLiteral)
