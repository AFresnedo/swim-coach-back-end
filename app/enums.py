from typing import Literal, get_args

StrokeLiteral = Literal["freestyle", "backstroke", "breaststroke", "butterfly", "individual_medley"]
CourseLiteral = Literal["scy", "scm", "lcm"]
SexLiteral = Literal["male", "female", "prefer_not_to_say"]
DeactivationReasonLiteral = Literal["reached", "abandoned", "other"]
UnitPreferenceLiteral = Literal["metric", "imperial"]

# Provisional starter taxonomy for SwimKnowledge classification - deliberately not
# final. Must be revisited once the hybrid-retrieval ticket defines its actual
# metadata-routing needs, before the step-4 ingestion prompt that populates these
# fields is built.
IngestionReasonLiteral = Literal["fallback_web_search"]
QualityFlagLiteral = Literal["pass", "reject"]
TopicCategoryLiteral = Literal[
    "technique", "drills", "training_science", "recovery", "nutrition", "race_strategy", "equipment"
]
SkillLevelLiteral = Literal["beginner", "intermediate", "advanced", "elite"]

STROKES: tuple[str, ...] = get_args(StrokeLiteral)
COURSES: tuple[str, ...] = get_args(CourseLiteral)
SEXES: tuple[str, ...] = get_args(SexLiteral)
DEACTIVATION_REASONS: tuple[str, ...] = get_args(DeactivationReasonLiteral)
UNIT_PREFERENCES: tuple[str, ...] = get_args(UnitPreferenceLiteral)
INGESTION_REASONS: tuple[str, ...] = get_args(IngestionReasonLiteral)
QUALITY_FLAGS: tuple[str, ...] = get_args(QualityFlagLiteral)
TOPIC_CATEGORIES: tuple[str, ...] = get_args(TopicCategoryLiteral)
SKILL_LEVELS: tuple[str, ...] = get_args(SkillLevelLiteral)
