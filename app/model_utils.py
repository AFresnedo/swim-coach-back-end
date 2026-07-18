from datetime import UTC, datetime

from sqlalchemy import ColumnElement, Enum, column, or_


# This function allows us to avoid freezing the timestamp when used as a mapped_column
# default in SQLAlchemy models. It'll be called once per row insertion, rather than
# once at import time, so each row gets a unique timestamp instead of all rows sharing
# the same one.
def utcnow() -> datetime:
    return datetime.now(UTC)


def enum_column(*values: str, name: str, length: int) -> Enum:
    """String-backed Enum column type, enforced with a real DB CHECK constraint.

    SQLAlchemy's Enum defaults create_constraint to False (no DB-level
    enforcement at all) and auto-sizes the VARCHAR to the longest member -
    both are passed explicitly here so callers can't omit them by accident,
    and so the emitted VARCHAR width matches whatever's already baked into
    migration history rather than whatever the current member list happens
    to need. name= must match the CheckConstraint name already present in
    the migration history, or alembic sees a drop-and-recreate instead of a
    no-op.
    """
    return Enum(*values, name=name, native_enum=False, create_constraint=True, length=length)


def in_clause(column_name: str, values: tuple[str, ...]) -> ColumnElement[bool]:
    return column(column_name).in_(values)


def nullable_in_clause(column_name: str, values: tuple[str, ...]) -> ColumnElement[bool]:
    return or_(column(column_name).is_(None), in_clause(column_name, values))
