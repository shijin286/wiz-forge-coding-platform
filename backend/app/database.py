from collections.abc import Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import BACKEND_DIR, get_settings


class Base(DeclarativeBase):
    pass


def normalize_url(url: str) -> str:
    # relative SQLite paths resolve against the backend folder, not the launch directory
    return url.replace("sqlite:///./", f"sqlite:///{BACKEND_DIR.as_posix()}/", 1)


def _make_engine(url: str):
    url = normalize_url(url)
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True)


engine = _make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _alembic_config():
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    cfg.attributes["skip_logging"] = True
    return cfg


def _add_missing_columns() -> None:
    """Bring a database created before migrations existed up to the baseline schema."""
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            existing = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name not in existing:
                    col_type = column.type.compile(dialect=engine.dialect)
                    conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN "{column.name}" {col_type}'))


def run_migrations() -> None:
    """Apply Alembic migrations on startup (creates the schema on a fresh database)."""
    from alembic import command

    from . import models  # noqa: F401  (register tables)

    cfg = _alembic_config()
    tables = set(inspect(engine).get_table_names())
    if "users" in tables and "alembic_version" not in tables:
        # created by the pre-migrations create_all(): align it with the baseline, then mark it as migrated
        _add_missing_columns()
        command.stamp(cfg, "head")
    with engine.begin() as connection:
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
