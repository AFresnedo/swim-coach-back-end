from datetime import UTC, datetime

from sqlalchemy import ColumnElement, column, or_


def utcnow() -> datetime:
    return datetime.now(UTC)


def in_clause(column_name: str, values: tuple[str, ...]) -> ColumnElement[bool]:
    return column(column_name).in_(values)


def nullable_in_clause(column_name: str, values: tuple[str, ...]) -> ColumnElement[bool]:
    return or_(column(column_name).is_(None), in_clause(column_name, values))
