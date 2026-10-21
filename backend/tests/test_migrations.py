"""The Alembic migrations must build exactly the schema the models describe."""

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

from app.database import Base, _alembic_config


def _migrate(url: str) -> None:
    engine = create_engine(url)
    cfg = _alembic_config()
    with engine.begin() as connection:
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")
    engine.dispose()


def test_migrations_match_models(tmp_path):
    url = f"sqlite:///{(tmp_path / 'fresh.db').as_posix()}"
    _migrate(url)
    engine = create_engine(url)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    engine.dispose()
    assert diff == [], f"models and migrations differ - run `alembic revision --autogenerate`: {diff}"


def test_migrations_are_idempotent(tmp_path):
    url = f"sqlite:///{(tmp_path / 'twice.db').as_posix()}"
    _migrate(url)
    _migrate(url)  # second run is a no-op
    engine = create_engine(url)
    with engine.connect() as conn:
        assert conn.execute(text("select version_num from alembic_version")).scalar() == "0001"
        assert {"users", "reviews", "findings"} <= set(inspect(conn).get_table_names())
    engine.dispose()
