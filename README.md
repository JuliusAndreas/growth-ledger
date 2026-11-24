# Growth Ledger

A personal growth tracker. You log what you learn each month, grouped by the medium you learned it from (books, algorithm problems, work challenges, and so on). Each month is a fresh sheet built from the same set of mediums, and a finished month gets a score.

It runs in two places from the same frontend file:

- **Self-hosted:** FastAPI + SQLite, packaged with Docker. This is what this repository deploys.
- **claude.ai artifact:** https://claude.ai/artifact/6YiHZK2PCiX44vszhuvzUF (private). Data lives in claude.ai's storage.

## Repository layout

```
artifact/index.html      The whole frontend (HTML, CSS, JS in one file)
backend/app/main.py      FastAPI app: REST API, sign-in, serves the frontend
backend/app/db.py        SQLite schema, default mediums, queries
backend/app/models.py    Validation for mediums, entries, months
backend/app/auth.py      scrypt password hashing, session check
backend/app/hashpw.py    CLI that prints a password hash for .env
backend/tests/           API tests (pytest)
Dockerfile, docker-compose.yml, .env.example
```

## Run it with Docker

```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(32))"      # paste as SECRET_KEY
docker compose build
docker compose run --rm -it growth-ledger python -m app.hashpw     # paste as ADMIN_PASSWORD_HASH
docker compose up -d
```

Open http://127.0.0.1:8000 and sign in with `ADMIN_USERNAME` and the password you hashed.

- Data is stored in the `growth-ledger-data` Docker volume at `/data/growth-ledger.db`.
- The six default mediums are created on first start. Their ids match the claude.ai artifact, so importing its export doesn't duplicate them.
- The compose file binds to `127.0.0.1` only. To reach it from other machines, put a reverse proxy with TLS in front (Caddy, nginx, Traefik) and set `COOKIE_SECURE=true`.

### Backups

The database is one SQLite file. Two ways to back it up:

```bash
# Copy the database out of the volume
docker compose cp growth-ledger:/data/growth-ledger.db ./growth-ledger-backup.db
```

Or use **Admin → Export JSON** in the app. The JSON export can be imported into any copy of Growth Ledger.

## Run it locally without Docker

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
export SECRET_KEY=dev-secret ADMIN_PASSWORD_HASH="$(.venv/bin/python -m app.hashpw)"
.venv/bin/uvicorn --factory app.main:create_app --reload
```

The database is created at `data/growth-ledger.db` in the repo root (git-ignored).

Run the tests:

```bash
cd backend && .venv/bin/python -m pytest
```

## Move your data from claude.ai

1. In the claude.ai artifact, open **Admin → Export JSON**.
2. In the self-hosted app, open **Admin → Import JSON…** and pick that file.

Import upserts every record by `id`. Records that exist only in the target stay as they are.

## Features

- **Monthly sheets:** one card per active medium. Each entry has a title, notes, an optional link, a date and a depth from 1 to 5 (Encountered, Understood, Applied, Shipped, Mastered/taught). Notes start collapsed.
- **Month score:** when a month ends, the app stores a score (0 to 100) and a snapshot of that month's mediums. Scoring is a placeholder for now: `computeMonthScore()` in `artifact/index.html` returns a random number.
- **Admin panel** (admin role only): add, edit, reorder, archive and restore mediums. Each medium has a weight that is stored for the future scoring formula.
- **Export and import:** Markdown export for reading, and a JSON export/import holding all the data.

## How the frontend runs in two places

`artifact/index.html` has no `<!doctype>`, `<html>`, `<head>` or `<body>` tags because claude.ai adds them when it publishes. The FastAPI server wraps the file the same way when it serves `/`.

At startup the page checks for `window.claude` (only present on claude.ai):

| | claude.ai | Self-hosted |
|---|---|---|
| Storage | the artifact's `db` capability | `restDb()` adapter → REST API → SQLite |
| Sign-in | static `USERS` list in the page (salted SHA-256) | `POST /api/login`, session cookie, `ADMIN_*` env vars (scrypt) |
| File export | `downloads` capability | browser download |

## API

All `/api/*` routes except `/api/login` need a signed-in session. Collections are `mediums`, `entries` and `months`. Writing `mediums` needs the admin role.

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/login` | `{username, password}` → sets the session cookie |
| POST | `/api/logout` | Clears the session |
| GET | `/api/me` | Current user |
| GET | `/api/{collection}` | List all documents |
| PUT | `/api/{collection}/{id}` | Create or replace a document |
| PATCH | `/api/{collection}/{id}` | Merge fields into an existing document |
| DELETE | `/api/{collection}/{id}` | Delete a document |
| GET | `/healthz` | Health check |

Interactive docs: `/api/docs`.

## Data model

| Table | Columns |
|---|---|
| `mediums` | `id`, `name`, `description`, `weight`, `sort_order`, `archived`, `created_at` |
| `entries` | `id`, `medium_id` → mediums, `date` (YYYY-MM-DD), `month` (YYYY-MM), `title`, `notes`, `link`, `depth` (1–5), `created_at`, `updated_at` |
| `months` | `id` (YYYY-MM), `score`, `mediums` (JSON snapshot), `finalized_at` |

The API and the JSON export use camelCase names (`mediumId`, `createdAt`, `order`, `finalizedAt`).

## JSON export format (version 1)

```json
{
  "app": "growth-ledger",
  "version": 1,
  "exportedAt": "2026-11-24T12:00:00.000Z",
  "mediums": [{ "id": "books", "name": "Books", "description": "...", "weight": 1, "order": 0, "archived": false, "createdAt": "..." }],
  "entries": [{ "id": "...", "mediumId": "books", "date": "2026-11-24", "month": "2026-11", "title": "...", "notes": "...", "link": "", "depth": 3, "createdAt": "...", "updatedAt": "..." }],
  "months":  [{ "id": "2026-10", "score": 57, "mediums": [ ... ], "finalizedAt": "..." }]
}
```

## Updating the claude.ai artifact

Edit `artifact/index.html`, then republish it to the same artifact URL (from Claude Code: publish this file with `url` set to the artifact link). Publishing without the URL creates a new artifact.

To change the artifact's password, generate a new salt and hash and replace them in `USERS`:

```bash
SALT=$(openssl rand -hex 8)
printf '%s' "$SALT:admin:<new password>" | sha256sum
```

Never commit a plain-text password.

## Roadmap

- [ ] Scoring formula (replace `computeMonthScore`)
- [ ] Daily sync of the JSON/Markdown export to Google Drive
- [ ] Multiple user accounts and profiles
