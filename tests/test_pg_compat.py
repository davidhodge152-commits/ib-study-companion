"""Tests for PostgreSQL compatibility layer."""

from __future__ import annotations

import pytest
from pg_compat import PgRow, _translate_sql, _translate_schema, is_postgres_url


class TestPgRow:
    """Test the PgRow dict-like interface."""

    def test_getitem_by_key(self):
        row = PgRow(["id", "name", "email"], (1, "Alice", "alice@test.com"))
        assert row["id"] == 1
        assert row["name"] == "Alice"
        assert row["email"] == "alice@test.com"

    def test_getitem_by_index(self):
        row = PgRow(["id", "name"], (42, "Bob"))
        assert row[0] == 42
        assert row[1] == "Bob"

    def test_keys(self):
        row = PgRow(["a", "b", "c"], (1, 2, 3))
        assert row.keys() == ["a", "b", "c"]

    def test_contains(self):
        row = PgRow(["id", "name"], (1, "Alice"))
        assert "id" in row
        assert "name" in row
        assert "email" not in row

    def test_get_with_default(self):
        row = PgRow(["id"], (1,))
        assert row.get("id") == 1
        assert row.get("missing", "default") == "default"

    def test_values(self):
        row = PgRow(["a", "b"], (10, 20))
        assert row.values() == [10, 20]

    def test_items(self):
        row = PgRow(["x", "y"], (1, 2))
        assert row.items() == [("x", 1), ("y", 2)]


class TestTranslateSQL:
    """Test SQL translation from SQLite to PostgreSQL."""

    def test_question_mark_to_percent_s(self):
        result = _translate_sql("SELECT * FROM users WHERE id = ?")
        assert result == "SELECT * FROM users WHERE id = %s"

    def test_multiple_placeholders(self):
        result = _translate_sql("INSERT INTO t (a, b, c) VALUES (?, ?, ?)")
        assert "%s, %s, %s" in result

    def test_insert_or_ignore(self):
        result = _translate_sql("INSERT OR IGNORE INTO users (id) VALUES (?)")
        assert "INSERT INTO" in result
        assert "ON CONFLICT DO NOTHING" in result
        assert "OR IGNORE" not in result

    def test_regular_insert_unchanged(self):
        result = _translate_sql("INSERT INTO users (name) VALUES (?)")
        assert "ON CONFLICT DO NOTHING" not in result

    def test_case_insensitive(self):
        result = _translate_sql("insert or ignore into t (a) values (?)")
        assert "ON CONFLICT DO NOTHING" in result


class TestTranslateSchema:
    """Test schema DDL translation."""

    def test_autoincrement_to_serial(self):
        result = _translate_schema("id INTEGER PRIMARY KEY AUTOINCREMENT")
        assert "SERIAL PRIMARY KEY" in result
        assert "AUTOINCREMENT" not in result

    def test_removes_pragma(self):
        result = _translate_schema("PRAGMA journal_mode=WAL;")
        assert "PRAGMA" not in result

    def test_preserves_other_sql(self):
        sql = "CREATE TABLE IF NOT EXISTS users (name TEXT NOT NULL)"
        result = _translate_schema(sql)
        assert result == sql


class TestIsPostgresUrl:
    """Test URL detection."""

    def test_postgresql_url(self):
        assert is_postgres_url("postgresql://user:pass@host/db") is True

    def test_postgres_url(self):
        assert is_postgres_url("postgres://user:pass@host/db") is True

    def test_sqlite_path(self):
        assert is_postgres_url("/path/to/db.sqlite") is False

    def test_empty_string(self):
        assert is_postgres_url("") is False


class TestDatabaseFallback:
    """Test that SQLite still works when PostgreSQL is not configured."""

    def test_sqlite_default(self, app):
        """Default config should use SQLite."""
        with app.app_context():
            from database import get_db
            db = get_db()
            # SQLite connection
            import sqlite3
            assert isinstance(db, sqlite3.Connection)

    def test_pg_compat_import(self):
        """pg_compat module should be importable."""
        import pg_compat
        assert hasattr(pg_compat, "connect_pg")
        assert hasattr(pg_compat, "PgConnectionWrapper")
        assert hasattr(pg_compat, "PgRow")
