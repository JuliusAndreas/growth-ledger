# Growth Ledger

A personal growth tracker. You log what you learn each month, grouped by the medium you learned it from (books, algorithm problems, work challenges, and so on). Each month is a fresh sheet built from the same set of mediums, and a finished month gets a score.

## Current state

The app runs as a private claude.ai artifact:
https://claude.ai/artifact/6YiHZK2PCiX44vszhuvzUF

```
artifact/index.html   The whole app: HTML, CSS and JS in one file, published as the artifact
```

`artifact/index.html` is written for the claude.ai artifact runtime. Two things to know about it:

- It has no `<!doctype>`, `<html>`, `<head>` or `<body>` tags. claude.ai wraps the file in that skeleton when it publishes.
- It stores data through the runtime's `db` capability (`window.claude.use("db")`) and saves files through `downloads`. Opened locally in a browser it loads, but it shows "Storage isn't available here" because those APIs only exist on claude.ai. Running it outside claude.ai needs the self-hosted backend (see Roadmap).

## Features

- **Monthly sheets:** one card per active medium. Each entry has a title, notes, an optional link, a date and a depth from 1 to 5 (Encountered, Understood, Applied, Shipped, Mastered/taught). Notes start collapsed.
- **Month score:** when a month ends, the app stores a score (0 to 100) and a snapshot of that month's mediums. Scoring is a placeholder for now: `computeMonthScore()` returns a random number.
- **Admin panel** (admin role only): add, edit, reorder, archive and restore mediums. Each medium has a weight that is stored for the future scoring formula.
- **Export and import:** Markdown export for reading, and a JSON export/import holding all the data.
- **Sign-in:** static accounts in the `USERS` array, with passwords stored as `sha256(salt + ":" + username + ":" + password)`. This only gates the screen. The data is protected by claude.ai's access rules: only the artifact's owner and editors can read or write it.

## Data model

| Collection | Document id | Fields |
|---|---|---|
| `mediums` | slug or random id | `name`, `description`, `weight`, `order`, `archived`, `createdAt` |
| `entries` | random id | `mediumId`, `date` (YYYY-MM-DD), `month` (YYYY-MM), `title`, `notes`, `link`, `depth` (1–5), `createdAt`, `updatedAt` |
| `months` | `YYYY-MM` | `score`, `mediums` (snapshot: `id`, `name`, `weight`, `archived`), `finalizedAt` |

## JSON export format (version 1)

This is the portability contract. The self-hosted version must be able to import it.

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

Import upserts every record by `id`. Records that exist only in the target stay as they are.

## Changing the app

1. Edit `artifact/index.html`.
2. Republish it to the same artifact URL (from Claude Code: publish this file with `url` set to the artifact link above), or the change creates a new artifact.

To change the password, generate a new salt and hash, then replace them in `USERS`:

```bash
SALT=$(openssl rand -hex 8)
printf '%s' "$SALT:admin:<new password>" | sha256sum
```

Never commit a plain-text password.

## Roadmap

- [ ] Scoring formula (replace `computeMonthScore`)
- [ ] Daily sync of the JSON/Markdown export to Google Drive
- [ ] Self-hosted version: FastAPI backend + this frontend, Docker packaging, JSON import
- [ ] Multiple user accounts and profiles
