# Spec: Registration

## Overview
Turn the existing `/register` page into a working sign-up flow. The page currently
only renders a form (`GET /register`); its `POST` submission has no handler. This
step adds server-side handling: validate the submitted name, email and password,
reject duplicate emails, hash the password with werkzeug, insert the user into the
`users` table, and redirect to the login page with a success message. Registration
is the first user-facing feature built on the Step 1 data layer and is a
prerequisite for login/logout (Step 3) and everything behind authentication.

## Depends on
- Step 1 — Database setup (`get_db()`, `init_db()`, `users` table with
  `UNIQUE` email constraint in `database/db.py`)

## Routes
- `GET /register` — render the registration form (already exists; keep it) — public
- `POST /register` — validate input, create the user, redirect to `login` on
  success or re-render `register.html` with an error on failure — public

Both are handled by the existing `register()` view via
`@app.route("/register", methods=["GET", "POST"])`. No other new routes.

## Database changes
No database changes. The existing `users` table (`id`, `name`, `email UNIQUE`,
`password_hash`, `created_at`) already supports registration.

New helper functions in `database/db.py` (no schema change):
- `get_user_by_email(email)` — return the `users` row for an email, or `None`
- `create_user(name, email, password)` — hash the password with
  `generate_password_hash`, insert the row with a parameterised query, commit,
  and return the new user id. Raise/propagate `sqlite3.IntegrityError` on a
  duplicate email so the route can show a friendly error even under a race.

## Templates
- **Create:** none
- **Modify:**
  - `templates/register.html`
    - Form `action` → `{{ url_for('register') }}` (no hardcoded `/register`)
    - Re-populate `name` and `email` fields with submitted values when an error
      is shown (never re-populate the password)
    - Add `minlength="8"` to the password input
  - `templates/login.html`
    - Render flashed messages (success message after registration) above the form
    - Form `action` → `{{ url_for('login') }}`
  - `templates/base.html`
    - Footer links `/terms` and `/privacy` → `url_for('terms')` / `url_for('privacy')`
      (fixes existing hardcoded URLs touched by this flow's layout)

## Files to change
- `app.py` — accept `POST` on `/register`; set `app.secret_key` (needed for
  `flash`); import `request`, `redirect`, `url_for`, `flash`; call the new db
  helpers
- `database/db.py` — add `get_user_by_email()` and `create_user()`
- `templates/register.html` — see Templates
- `templates/login.html` — see Templates
- `templates/base.html` — see Templates
- `static/css/style.css` — add an `.auth-success` message style (mirrors
  `.auth-error`, using `--accent` / `--accent-light`)

## Files to create
- `tests/test_registration.py` — pytest tests covering the definition of done
  (use a temporary database path so tests never touch `expense_tracker.db`)

## New dependencies
No new dependencies. Uses `flask`, `werkzeug.security` and `sqlite3`, all
already available via `requirements.txt` / the standard library.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only (`?` placeholders) — never f-strings or `%` in SQL
- Passwords hashed with werkzeug (`generate_password_hash`) — never store plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- All DB access lives in `database/db.py`; the route only calls helpers
- Use `url_for()` for every internal link and redirect
- Do not implement login sessions, `/logout`, or `/profile` — those are later steps
- Validation (server-side, regardless of HTML `required` attributes):
  - `name`: required after stripping whitespace
  - `email`: required, stripped and lowercased, must contain `@` and a `.` after it
  - `password`: required, at least 8 characters
- Show one clear error message per failed submission; status 200 with the form re-rendered
- Duplicate email error text: "An account with that email already exists."
- `app.secret_key` read from the `SECRET_KEY` environment variable with a
  dev-only fallback; do not commit a real secret
- App must still run on port 5001

## Definition of done
- [ ] `GET /register` renders the form with no errors
- [ ] Submitting valid name, email and an 8+ character password creates a row
      in `users` and redirects to `/login`
- [ ] The login page shows a success message after registering
- [ ] The stored `password_hash` is a werkzeug hash, not the plaintext password,
      and `check_password_hash` verifies it
- [ ] Registering with an email that already exists (including different case,
      e.g. `Demo@Spendly.com`) shows "An account with that email already exists."
      and creates no new row
- [ ] Submitting a blank name, an invalid email, or a password under 8 characters
      re-renders the form with an error and creates no row
- [ ] After an error, the name and email fields keep the submitted values; the
      password field is empty
- [ ] No hardcoded internal URLs remain in `register.html`, `login.html` or `base.html`
- [ ] `pytest` passes, including `tests/test_registration.py`
- [ ] `python app.py` starts on port 5001 without errors
