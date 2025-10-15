import logging
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from .config import DB_URI
from .exceptions import CheckpointerError

logger = logging.getLogger(__name__)

_connection_pool = None
_checkpointer = None


async def get_checkpointer() -> AsyncPostgresSaver:
    """Get or initialize the PostgreSQL checkpointer for LangGraph state persistence."""
    global _connection_pool, _checkpointer

    try:
        if _checkpointer is None:
            if _connection_pool is None:
                _connection_pool = AsyncConnectionPool(
                    conninfo=DB_URI,
                    min_size=1,
                    max_size=20,
                    timeout=30,
                    kwargs={
                        'autocommit': True,
                        'prepare_threshold': None
                    }
                )
            _checkpointer = AsyncPostgresSaver(_connection_pool)
            await _checkpointer.setup()
        return _checkpointer
    except Exception as e:
        logger.error(
            f"Checkpointer error: {e}",
            exc_info=True
        )
        raise CheckpointerError('Error while getting the database connection') from e


async def close_checkpointer() -> None:
    """Close the database connection pool."""
    try:
        global _connection_pool
        if _connection_pool:
            await _connection_pool.close()
    except Exception as e:
        logger.error(
            f"Checkpointer cleanup error: {e}",
            exc_info=True
        )
