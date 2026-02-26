"""
Database module for the Chinook SQLite database.
Handles downloading, loading, and providing access to the sample database.
"""

import sqlite3
import requests
import logging
from langchain_community.utilities.sql_database import SQLDatabase
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

_engine = None
_db = None

CHINOOK_SQL_URL = (
    "https://raw.githubusercontent.com/lerocha/chinook-database/"
    "master/ChinookDatabase/DataSources/Chinook_Sqlite.sql"
)


def _create_engine():
    """Download Chinook SQL script and create an in-memory SQLite engine."""
    logger.info("Downloading Chinook database SQL script...")
    response = requests.get(CHINOOK_SQL_URL, timeout=60)
    response.raise_for_status()
    sql_script = response.text

    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.executescript(sql_script)
    logger.info("Chinook database loaded successfully into memory.")

    return create_engine(
        "sqlite://",
        creator=lambda: connection,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )


def get_engine():
    """Get or create the SQLAlchemy engine (singleton)."""
    global _engine
    if _engine is None:
        _engine = _create_engine()
    return _engine


def get_db() -> SQLDatabase:
    """Get or create the LangChain SQLDatabase instance (singleton)."""
    global _db
    if _db is None:
        _db = SQLDatabase(get_engine())
    return _db


def verify_database() -> bool:
    """Verify the database is loaded and accessible."""
    try:
        db = get_db()
        result = db.run("SELECT COUNT(*) FROM Customer;")
        logger.info(f"Database verification OK. Customer count query returned: {result}")
        return True
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        return False
