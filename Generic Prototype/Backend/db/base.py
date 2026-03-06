"""Async SQLAlchemy engine and session. Use get_db() in route dependencies."""
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Avoid circular import: use env or default if core not yet loaded
try:
    from core.config import settings
    DATABASE_URL_ASYNC = settings.DATABASE_URL_ASYNC
    DEBUG = settings.DEBUG
except Exception:
    DATABASE_URL_ASYNC = os.getenv("DATABASE_URL_ASYNC", "sqlite+aiosqlite:///./configurator.db")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# SQLite path relative to backend directory
if DATABASE_URL_ASYNC.startswith("sqlite"):
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if ":///./" in DATABASE_URL_ASYNC:
        db_file = DATABASE_URL_ASYNC.split(":///./")[-1]
        DATABASE_URL_ASYNC = f"sqlite+aiosqlite:///{os.path.join(backend_dir, db_file)}"

async_engine = create_async_engine(
    DATABASE_URL_ASYNC,
    echo=DEBUG,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


Base = declarative_base()
