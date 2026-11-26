# Plan: Step 1 — Database Setup (Spendly)

## Context
`database/db.py` is only a comment stub and nothing in `app.py` touches the DB. Spec `.claude/specs/01-database-setp.md` asks for a working SQLite data layer (`get_db`, `init_db`, `seed_db`) wired into app startup — the foundation for auth (Step 3+) and expenses (Steps 7–9). No new routes, no new packages.

First action after approval: save this plan to `.claude/plan/01-databasesetup.md` (as requested).

## Decisions
- **DB file:** `expense_tracker.db` in project root (already in `.gitignore`), path anchored via `os.path` from `db.py`'s location (not CWD) and held in module-level `DB_PATH`.
- **Startup calls at module level** in `app.py` (right after `app = Flask(__name__)`), not under `__main__`, so `flask run`/imports also get a ready DB. Both functions are idempotent, so the debug reloader's double import is harmless.
- **Connections closed explicitly** with `try/finally: conn.close()` (sqlite3's `with conn` commits but does not close; matters for Windows file locks).
- **Categories:** module-level `CATEGORIES` tuple (single source of truth for later steps) **plus** a `CHECK (category IN (...))` on `expenses.category`; also `CHECK (amount > 0)`. No DB exists yet, so no migration concern.
- **Seed dates:** `today.replace(day=min(d, today.day)).isoformat()` — always in current month, never in the future, YYYY-MM-DD.
- **Seed is one transaction:** user + 8 expenses committed together; early return if `users` has any row.
- FK uses default `ON DELETE` behaviour (no cascade needed yet).

## Changes

### `database/db.py` (replace stub)
- Imports: `os`, `sqlite3`, `date`, `werkzeug.security.generate_password_hash`.
- `DB_PATH`, `CATEGORIES`, `SCHEMA` (two `CREATE TABLE IF NOT EXISTS` per spec schema + CHECKs; `created_at TEXT DEFAULT (datetime('now'))`; `user_id INTEGER NOT NULL REFERENCES users(id)`).
- `get_db()`: connect to `DB_PATH`, `row_factory = sqlite3.Row`, `PRAGMA foreign_keys = ON`, return conn.
- `init_db()`: `executescript(SCHEMA)` (static DDL, no user input), commit, close.
- `seed_db()`: `SELECT 1 FROM users LIMIT 1` → return if found; insert Demo User / `demo@spendly.com` / `generate_password_hash("demo123")` with `?` placeholders; `executemany` 8 expenses for `lastrowid`, rupee-scale amounts, all 7 categories covered (Food twice), one with `description=None`; commit; close.

Sample rows (day offsets 1,3,5,8,11,14,18,22):
Food 450.00 Groceries · Transport 120.00 Auto fare · Bills 1850.00 Electricity bill · Health 600.00 Pharmacy · Entertainment 350.00 Movie tickets · Shopping 2499.00 New shoes · Other 200.00 (no description) · Food 280.00 Lunch out.

### `app.py`
```python
from flask import Flask, render_template
from database.db import get_db, init_db, seed_db

app = Flask(__name__)

with app.app_context():
    init_db()
    seed_db()
```
Routes and `app.run(debug=True, port=5001)` unchanged.

## Verification (project root, venv active) — run/confirmed via a subagent per CLAUDE.md
1. Delete any local `expense_tracker.db`; `python -c "import app"` → file created in project root.
2. Run counts twice: users=1, expenses=8 both times (no duplicate seeding).
3. Distinct categories = all 7; every date `YYYY-MM-DD`, current month, ≤ today.
4. `check_password_hash(stored, "demo123")` → `True`, stored value is a hash (not plaintext).
5. Insert expense with `user_id=9999` → `IntegrityError: FOREIGN KEY constraint failed`.
6. Insert duplicate `demo@spendly.com` → `IntegrityError: UNIQUE constraint failed: users.email`.
7. `PRAGMA foreign_keys` on a `get_db()` connection → `1`.
8. `python app.py`, open http://127.0.0.1:5001/ → landing renders, no traceback.

No `tests/` file is added (spec lists no files to create); checks above are ad-hoc scripts.
