from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def sql_in_clause(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(f"'{value}'" for value in values)})"


def nullable_sql_in_clause(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IS NULL OR {sql_in_clause(column, values)}"
