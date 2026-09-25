import pytest

from market_intel.db import _normalize_database_url


@pytest.mark.parametrize(
    "raw, expected",
    [
        # No explicit driver: pin psycopg2 (SQLAlchemy 2.1 defaults to psycopg 3).
        ("postgresql://u:p@host:5432/db?sslmode=require", "postgresql+psycopg2://u:p@host:5432/db?sslmode=require"),
        # Heroku/Supabase-style scheme, which SQLAlchemy rejects outright.
        ("postgres://u:p@host:5432/db", "postgresql+psycopg2://u:p@host:5432/db"),
        # Already explicit: left alone.
        ("postgresql+psycopg2://u:p@host/db", "postgresql+psycopg2://u:p@host/db"),
        ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        # Non-Postgres URLs (tests use SQLite) are untouched.
        ("sqlite:///tmp/test.db", "sqlite:///tmp/test.db"),
    ],
)
def test_normalize_database_url(raw, expected):
    assert _normalize_database_url(raw) == expected
