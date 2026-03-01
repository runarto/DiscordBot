import pytest
from db.db_interface import DB

ELITE_LEAGUE_ID = 103
OBOS_LEAGUE_ID = 104


@pytest.fixture
def db():
    """Fresh in-memory SQLite database for each test."""
    return DB(":memory:")
