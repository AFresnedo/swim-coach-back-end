from logging.config import fileConfig

from sqlalchemy import create_engine, pool

import app.goal.model  # noqa: F401
import app.profile.model  # noqa: F401
import app.rag.models  # noqa: F401
import app.swim_time.model  # noqa: F401
import app.user.model  # noqa: F401
from alembic import context
from app.database import StandardBase, VectorBase
from app.db_config import database_settings

config = context.config
config.set_main_option("sqlalchemy.url", database_settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = [StandardBase.metadata, VectorBase.metadata]


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connect_args = {"check_same_thread": False} if database_settings.database_url.startswith("sqlite") else {}
    connectable = create_engine(database_settings.database_url, poolclass=pool.NullPool, connect_args=connect_args)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
