import pytest
from ponto_esa_v5.database_postgresql import USE_POSTGRESQL

@pytest.fixture(scope="session", autouse=True)
def configure_postgresql():
    """Configure the database to use PostgreSQL for testing."""
    global USE_POSTGRESQL
    USE_POSTGRESQL = True
    print("Configured to use PostgreSQL for testing.")