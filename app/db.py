from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create the application database engine on first use."""
    return create_engine(get_settings().database_url, pool_pre_ping=True)
