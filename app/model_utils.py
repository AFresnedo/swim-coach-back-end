from datetime import UTC, datetime

from sqlalchemy import ColumnElement, column, or_


# This function allows us to avoid freezing the timestamp when used as a mapped_column
# default in SQLAlchemy models. It'll be called once per row insertion, rather than
# once at import time, so each row gets a unique timestamp instead of all rows sharing
# the same one.
def utcnow() -> datetime:
    return datetime.now(UTC)


def in_clause(column_name: str, values: tuple[str, ...]) -> ColumnElement[bool]:
    return column(column_name).in_(values)


def nullable_in_clause(column_name: str, values: tuple[str, ...]) -> ColumnElement[bool]:
    return or_(column(column_name).is_(None), in_clause(column_name, values))
