import os
import sqlite3
from datetime import date

from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get(
    "SPENDLY_DB_PATH", os.path.join(BASE_DIR, "expense_tracker.db")
)

CATEGORIES = (
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    amount      REAL NOT NULL CHECK (amount > 0),
    category    TEXT NOT NULL CHECK (category IN (
                    'Food', 'Transport', 'Bills', 'Health',
                    'Entertainment', 'Shopping', 'Other'
                )),
    date        TEXT NOT NULL,
    description TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);
"""


def get_db():
    """Return a SQLite connection with dict-like rows and FK enforcement."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables. Safe to call repeatedly."""
    conn = get_db()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def get_user_by_email(email):
    """Return the users row for an email (case-insensitive), or None."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT id, name, email, password_hash, created_at "
            "FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()
    finally:
        conn.close()


def create_user(name, email, password):
    """Insert a user with a hashed password and return the new id.

    Raises sqlite3.IntegrityError if the email is already registered.
    """
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email.strip().lower(), generate_password_hash(password)),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def seed_db():
    """Insert a demo user and sample expenses, only if no users exist."""
    conn = get_db()
    try:
        if conn.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            return

        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
        )
        user_id = cur.lastrowid

        today = date.today()

        def day(d):
            # Keep every date in the current month and never in the future.
            return today.replace(day=min(d, today.day)).isoformat()

        samples = [
            (450.00, "Food", day(1), "Groceries"),
            (120.00, "Transport", day(3), "Auto fare"),
            (1850.00, "Bills", day(5), "Electricity bill"),
            (600.00, "Health", day(8), "Pharmacy"),
            (350.00, "Entertainment", day(11), "Movie tickets"),
            (2499.00, "Shopping", day(14), "New shoes"),
            (200.00, "Other", day(18), None),
            (280.00, "Food", day(22), "Lunch out"),
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            [(user_id, *row) for row in samples],
        )
        conn.commit()
    finally:
        conn.close()
