import os

import pytest
from werkzeug.security import check_password_hash

import app as app_module
import database.db as db_module

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DUPLICATE_MSG = "An account with that email already exists."
VALID = {"name": "Asha Rao", "email": "asha@example.com", "password": "secret123"}


def user_count(conn):
    return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def test_get_register_renders_form(client):
    resp = client.get("/register")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "<form" in html
    assert 'minlength="8"' in html
    assert "auth-error" not in html


def test_valid_registration_creates_user_and_redirects(client, db_conn):
    resp = client.post("/register", data={**VALID, "email": "Asha@Example.com"})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")
    row = db_conn.execute(
        "SELECT name, email FROM users WHERE email = ?", ("asha@example.com",)
    ).fetchone()
    assert row is not None
    assert row["name"] == "Asha Rao"


def test_success_message_on_login_after_register(client):
    resp = client.post("/register", data=VALID, follow_redirects=True)
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "Account created! Please sign in." in html
    assert "auth-success" in html


def test_password_is_hashed(client, db_conn):
    client.post("/register", data=VALID)
    stored = db_conn.execute(
        "SELECT password_hash FROM users WHERE email = ?", (VALID["email"],)
    ).fetchone()["password_hash"]
    assert stored != VALID["password"]
    assert VALID["password"] not in stored
    assert check_password_hash(stored, VALID["password"])
    assert not check_password_hash(stored, "wrongpassword")


@pytest.mark.parametrize(
    "email", ["demo@spendly.com", "Demo@Spendly.com", "  DEMO@spendly.com "]
)
def test_duplicate_email_rejected(client, db_conn, email):
    before = user_count(db_conn)
    resp = client.post("/register", data={**VALID, "email": email})
    assert resp.status_code == 200
    assert DUPLICATE_MSG in resp.get_data(as_text=True)
    assert user_count(db_conn) == before


def test_integrity_error_race_shows_friendly_error(client, db_conn, monkeypatch):
    # Simulate another request inserting the email between check and insert.
    monkeypatch.setattr(app_module, "get_user_by_email", lambda email: None)
    before = user_count(db_conn)
    resp = client.post("/register", data={**VALID, "email": "demo@spendly.com"})
    assert resp.status_code == 200
    assert DUPLICATE_MSG in resp.get_data(as_text=True)
    assert user_count(db_conn) == before


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": ""},
        {"name": "   "},
        {"email": "notanemail"},
        {"email": "a@b"},
        {"email": "@x.com"},
        {"email": "a@.com"},
        {"email": ""},
        {"password": "short12"},
        {"password": ""},
    ],
)
def test_invalid_input_rerenders_with_error(client, db_conn, overrides):
    before = user_count(db_conn)
    resp = client.post("/register", data={**VALID, **overrides})
    assert resp.status_code == 200
    assert "auth-error" in resp.get_data(as_text=True)
    assert user_count(db_conn) == before


def test_fields_repopulated_password_cleared(client):
    data = {**VALID, "password": "short12"}
    html = client.post("/register", data=data).get_data(as_text=True)
    assert 'value="Asha Rao"' in html
    assert 'value="asha@example.com"' in html
    assert "short12" not in html


@pytest.mark.parametrize("template", ["register.html", "login.html", "base.html"])
def test_no_hardcoded_internal_urls(template):
    with open(os.path.join(PROJECT_ROOT, "templates", template), encoding="utf-8") as f:
        source = f.read()
    for bad in ('action="/', 'href="/'):
        assert bad not in source


def test_real_db_untouched(app):
    real = os.path.join(PROJECT_ROOT, "expense_tracker.db")
    assert os.path.abspath(db_module.DB_PATH) != os.path.abspath(real)
