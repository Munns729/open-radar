import asyncio
from logging.config import fileConfig
import sys
import os

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Add src to path so we can import modules
sys.path.append(os.getcwd())

from src.core.config import settings
from src.core.database import Base, engine as app_engine

# Import all models to ensure they are registered in Base.metadata
# We import the module that contains the model definitions (usually database.py)
from src.universe import database  # noqa
from src.capital import database  # noqa
from src.deal_intelligence import database  # noqa
from src.tracker import database  # noqa
from src.competitive import database  # noqa
from src.relationships import database  # noqa
from src.market_intelligence import database  # noqa
from src.reporting import database  # noqa
from src.carveout import database  # noqa
from src.capability import database  # noqa
from src.canon import database  # noqa
from src.resilience import database  # noqa
from src.documents import database as documents_db  # noqa

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# Retrieve URL from settings
def get_url():
    return settings.database_url

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    # Handle asyncpg in offline mode if needed, but usually we just want the string
    # If the driver is asyncpg, offline mode might complain if it tries to load usage
    # but strictly speaking offline mode just generates SQL.
    # However, to be safe, we can use the sync driver for offline mode or
    # just let it be.
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Use the app's async engine
    connectable = app_engine

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
