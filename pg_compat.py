"""PostgreSQL compatibility layer — wraps psycopg2 to match sqlite3 API.

When DATABASE_URL starts with postgresql://, this module provides a
connection wrapper that translates:
  - ? placeholders → %s
  - INSERT OR IGNORE → INSERT ... ON CONFLICT DO NOTHING
  - executescript() → split and execute
  - Row factory → dict-like Row objects
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class PgRow:
    """Dict-like row that mimics sqlite3.Row."""

    def __init__(self, columns: list[str], values: tuple):
        self._data = dict(zip(columns, values))

    def __getitem__(self, key: str | int) -> Any:
        if isinstance(key, int):
            return list(self._data.values())[key]
        return self._data[key]

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def keys(self) -> list[str]:
        return list(self._data.keys())

    def values(self) -> list[Any]:
        return list(self._data.values())

    def items(self) -> list[tuple[str, Any]]:
        return list(self._data.items())

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def __repr__(self) -> str:
        return f"PgRow({self._data})"


def _translate_sql(sql: str) -> str:
    """Translate SQLite SQL to PostgreSQL SQL."""
    # Replace ? with %s for parameterized queries
    translated = sql.replace("?", "%s")

    # INSERT OR IGNORE → INSERT ... ON CONFLICT DO NOTHING
    translated = re.sub(
        r"INSERT\s+OR\s+IGNORE\s+INTO",
        "INSERT INTO",
        translated,
        flags=re.IGNORECASE,
    )
    if "ON CONFLICT" not in translated.upper() and "INSERT INTO" in translated.upper():
        # Only add ON CONFLICT DO NOTHING for translated INSERT OR IGNORE
        if "INSERT OR IGNORE" in sql.upper():
            # Find the VALUES(...) part and append ON CONFLICT DO NOTHING
            translated = translated.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"

    return translated


def _translate_schema(sql: str) -> str:
    """Translate SQLite schema DDL to PostgreSQL DDL."""
    translated = sql

    # INTEGER PRIMARY KEY AUTOINCREMENT → SERIAL PRIMARY KEY
    translated = re.sub(
        r"(\w+)\s+INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT",
        r"\1 SERIAL PRIMARY KEY",
        translated,
        flags=re.IGNORECASE,
    )

    # Remove SQLite-specific PRAGMAs
    translated = re.sub(r"PRAGMA\s+\w+\s*=\s*\w+\s*;?", "", translated, flags=re.IGNORECASE)

    # UNIQUE(col1, col2) constraints are the same in both

    return translated


class PgCursorWrapper:
    """Wraps a psycopg2 cursor to match sqlite3.Cursor interface."""

    def __init__(self, cursor):
        self._cursor = cursor
        self._columns: list[str] = []

    @property
    def lastrowid(self) -> int | None:
        """Return last inserted row ID (uses RETURNING in PostgreSQL)."""
        return self._last_id

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    @property
    def description(self):
        return self._cursor.description

    def execute(self, sql: str, params: tuple = ()) -> "PgCursorWrapper":
        translated = _translate_sql(sql)
        self._last_id = None

        # For INSERT statements, add RETURNING id to capture lastrowid
        upper = translated.strip().upper()
        if upper.startswith("INSERT") and "RETURNING" not in upper:
            # Try to add RETURNING for id column
            try:
                self._cursor.execute(translated + " RETURNING id", params)
                row = self._cursor.fetchone()
                if row:
                    self._last_id = row[0]
                return self
            except Exception:
                # If RETURNING id fails (e.g., table has no id column), fall back
                pass

        self._cursor.execute(translated, params)
        if self._cursor.description:
            self._columns = [desc[0] for desc in self._cursor.description]
        return self

    def fetchone(self) -> PgRow | None:
        row = self._cursor.fetchone()
        if row is None:
            return None
        if self._cursor.description:
            columns = [desc[0] for desc in self._cursor.description]
            return PgRow(columns, row)
        return PgRow([], ())

    def fetchall(self) -> list[PgRow]:
        rows = self._cursor.fetchall()
        if not rows or not self._cursor.description:
            return []
        columns = [desc[0] for desc in self._cursor.description]
        return [PgRow(columns, row) for row in rows]

    def close(self):
        self._cursor.close()


class PgConnectionWrapper:
    """Wraps a psycopg2 connection to match sqlite3.Connection interface."""

    def __init__(self, conn):
        self._conn = conn
        self._conn.autocommit = False
        self.row_factory = None  # Compatibility with sqlite3

    def execute(self, sql: str, params: tuple = ()) -> PgCursorWrapper:
        cursor = PgCursorWrapper(self._conn.cursor())
        cursor.execute(sql, params)
        return cursor

    def executescript(self, sql: str) -> None:
        """Execute multiple SQL statements (PostgreSQL equivalent)."""
        translated = _translate_schema(sql)
        # Split on semicolons, filter empty
        statements = [s.strip() for s in translated.split(";") if s.strip()]
        cursor = self._conn.cursor()
        for stmt in statements:
            try:
                cursor.execute(stmt)
            except Exception as e:
                # Handle "already exists" and "duplicate column" gracefully
                err_msg = str(e).lower()
                if any(phrase in err_msg for phrase in [
                    "already exists", "duplicate column", "does not exist",
                ]):
                    self._conn.rollback()
                    logger.debug("Skipping migration statement: %s", e)
                else:
                    raise
        cursor.close()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def cursor(self):
        return PgCursorWrapper(self._conn.cursor())


def connect_pg(database_url: str) -> PgConnectionWrapper:
    """Create a PostgreSQL connection with sqlite3-compatible interface."""
    try:
        import psycopg2
    except ImportError:
        raise ImportError(
            "psycopg2 is required for PostgreSQL support. "
            "Install it with: pip install psycopg2-binary"
        )

    conn = psycopg2.connect(database_url)
    return PgConnectionWrapper(conn)


def is_postgres_url(url: str) -> bool:
    """Check if a database URL is a PostgreSQL URL."""
    return url.startswith("postgresql://") or url.startswith("postgres://")
