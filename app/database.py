"""Database integration boundary.

The SQLite engine and session factory will be added here at the database stage.
Keeping the URL in one module prevents future persistence details from leaking
into routers and services.
"""

from app.config import settings

DATABASE_URL = settings.database_url


def initialize_database() -> None:
    """Initialize persistence when a database implementation is introduced."""

    return None
