# ──── Usage Guide ────
# MODULE CODE (src/*/workflow.py, src/*/service.py):
#   Use async sessions: async_session_factory, get_db, get_async_db
#   Pattern: async with get_async_db() as session:
#                result = await session.execute(select(Model).where(...))
#
# SCRIPTS ONLY (scripts/*/):
#   Use sync sessions: sync_session_factory, get_sync_db
#   Pattern: with get_sync_db() as session:
#                results = session.query(Model).filter(...).all()
#
# Never use sync sessions in module code. Never use async sessions in scripts.
#
# DATABASE: PostgreSQL only. Run via docker-compose up -d.

from contextlib import contextmanager, asynccontextmanager
import sys

# Standardize module naming to prevent dual-import split of SQLAlchemy Base registry
if 'core.database' in sys.modules and 'src.core.database' not in sys.modules:
    sys.modules['src.core.database'] = sys.modules['core.database']
elif 'src.core.database' in sys.modules and 'core.database' not in sys.modules:
    sys.modules['core.database'] = sys.modules['src.core.database']

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy import MetaData
from src.core.config import settings


class ToDictMixin:
    """Mixin to add dictionary serialization to models."""
    def to_dict(self):
        """Convert model instance to dictionary."""
        from sqlalchemy import inspect
        import datetime
        from decimal import Decimal
        from enum import Enum

        result = {}
        for key in inspect(self).mapper.column_attrs.keys():
            value = getattr(self, key)
            if isinstance(value, datetime.datetime):
                result[key] = value.isoformat()
            elif isinstance(value, datetime.date):
                result[key] = value.isoformat()
            elif isinstance(value, Decimal):
                result[key] = float(value)
            elif isinstance(value, Enum):
                result[key] = value.value
            else:
                result[key] = value
        return result


class Base(ToDictMixin, DeclarativeBase):
    metadata = MetaData()


# ──── Single Async Engine (PostgreSQL + asyncpg) ────
db_url = settings.database_url
if db_url.startswith("postgresql://") and "asyncpg" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(db_url, echo=False, future=True)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# ──── Single Sync Engine (Scripts Only — PostgreSQL + psycopg2) ────
sync_db_url = settings.database_url
if sync_db_url.startswith("postgresql+asyncpg://"):
    sync_db_url = sync_db_url.replace("postgresql+asyncpg://", "postgresql://")

sync_engine = create_engine(
    sync_db_url,
    echo=False,
)

sync_session_factory = sessionmaker(
    sync_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ──── Session Providers (FastAPI Dependencies) ────
async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


# ──── Context Managers ────
@contextmanager
def get_sync_db() -> Generator[Session, None, None]:
    session = sync_session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@asynccontextmanager
async def get_async_db() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ──── End of Database Configuration ────
