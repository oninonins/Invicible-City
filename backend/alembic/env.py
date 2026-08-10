import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure /app is importable (alembic runs with WORKDIR /app)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.base import Base
# Model imports register tables into Base.metadata for autogenerate (intentionally unused).
from app.models.etl import DatasetMetadata, ETLJob  # noqa: F401
from app.models.facility import Facility  # noqa: F401
from app.models.spatial import City, District, Province, Village  # noqa: F401
from app.models.ufs import UfsIndicator, UfsScore  # noqa: F401
from app.models.user import User  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

if settings.DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
else:
    SQLALCHEMY_DATABASE_URL = (
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )
config.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (executed against live DB)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
