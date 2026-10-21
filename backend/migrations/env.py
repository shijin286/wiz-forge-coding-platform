from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app import models  # noqa: F401  (registers the tables on Base.metadata)
from app.config import get_settings
from app.database import Base, normalize_url

config = context.config
# the app configures logging itself; only the alembic CLI should apply alembic.ini's logging
if config.config_file_name is not None and not config.attributes.get("skip_logging"):
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", normalize_url(get_settings().database_url).replace("%", "%%"))
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata,
                      literal_binds=True, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = config.attributes.get("connection")
    if connectable is None:
        connectable = engine_from_config(config.get_section(config.config_ini_section, {}),
                                         prefix="sqlalchemy.", poolclass=pool.NullPool)
        with connectable.connect() as connection:
            _run(connection)
    else:
        _run(connectable)


def _run(connection) -> None:
    # batch mode lets ALTER-style migrations work on SQLite too
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
