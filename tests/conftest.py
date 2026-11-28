import os
import sqlite3
import sys
import tempfile

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Must be set before `app` is imported: importing it runs init_db()/seed_db(),
# and this keeps that away from the real expense_tracker.db.
os.environ["SPENDLY_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "import.db")
os.environ.setdefault("SECRET_KEY", "test-secret")

import app as app_module  # noqa: E402
import database.db as db_module  # noqa: E402


@pytest.fixture
def app(monkeypatch, tmp_path):
    """Flask app backed by a fresh, seeded database for each test."""
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test.db"))
    db_module.init_db()
    db_module.seed_db()
    app_module.app.config["TESTING"] = True
    yield app_module.app


@pytest.fixture
def db_conn(app):
    """Raw connection to the test database for assertions."""
    conn = sqlite3.connect(db_module.DB_PATH)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()
