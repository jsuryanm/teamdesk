from collections.abc import AsyncIterator
# loops over items one by one when getting each item requires waiting for a slow operaiton 

from sqlalchemy.ext.asyncio import (
    AsyncSession, 
    async_sessionmaker,
    create_async_engine
)
# AsyncSession is a tool that lets the code talk to db asynchronously
# create_async_engine creates async connection pool to db.

from sqlalchemy.pool import NullPool
# NullPool is a connection pooling class in sqlalchemy that completely disables connection pooling
# NullPOol opens a brand new connection every time the code needs to talk with the db and immediately closes them
from backend.app.core.config import get_settings

settings = get_settings()

if settings.environment == 'test':
    pool_options: dict = {"poolclass": NullPool}

else:
    pool_options = {
        "pool_size": settings.db_pool_size, 
        "max_overflow": settings.db_max_overflow,
        "pool_pre_ping": True
    }

engine = create_async_engine(settings.database_url, **pool_options)

SessionLocal = async_sessionmaker(bind=engine, 
                                  expire_on_commit=False,
                                  autoflush=False)

async def get_db() -> AsyncIterator[AsyncSession]:
    """One session per request; always closed"""
    async with SessionLocal() as session: 
        yield session