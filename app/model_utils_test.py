from datetime import UTC, datetime, timedelta

from app.model_utils import enum_column, in_clause, nullable_in_clause, utcnow


def _compiled(clause) -> str:
    return str(clause.compile(compile_kwargs={"literal_binds": True}))


def test_utcnow_is_timezone_aware_utc_and_current():
    before = datetime.now(UTC)
    result = utcnow()
    after = datetime.now(UTC)

    assert result.tzinfo == UTC
    assert before - timedelta(seconds=1) <= result <= after + timedelta(seconds=1)


def test_enum_column_enforces_a_real_check_constraint_with_the_given_name_and_length():
    column_type = enum_column("a", "bb", name="ck_test_thing", length=10)

    assert column_type.create_constraint is True
    assert column_type.native_enum is False
    assert column_type.name == "ck_test_thing"
    assert column_type.length == 10
    assert set(column_type.enums) == {"a", "bb"}


def test_in_clause_builds_an_in_expression():
    assert _compiled(in_clause("stroke", ("freestyle", "backstroke"))) == "stroke IN ('freestyle', 'backstroke')"


def test_nullable_in_clause_also_allows_null():
    compiled = _compiled(nullable_in_clause("stroke", ("freestyle", "backstroke")))
    assert compiled == "stroke IS NULL OR stroke IN ('freestyle', 'backstroke')"
