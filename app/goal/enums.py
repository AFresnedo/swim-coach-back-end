from typing import Literal, get_args

DeactivationReasonLiteral = Literal["reached", "abandoned", "other"]

DEACTIVATION_REASONS: tuple[str, ...] = get_args(DeactivationReasonLiteral)
