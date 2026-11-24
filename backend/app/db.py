"""SQLite storage. One table per collection; the API speaks the same JSON shape as
the claude.ai artifact and its JSON export (camelCase fields, string ids)."""
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS mediums (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    weight      REAL NOT NULL DEFAULT 1,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    archived    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT
);
CREATE TABLE IF NOT EXISTS entries (
    id          TEXT PRIMARY KEY,
    medium_id   TEXT NOT NULL REFERENCES mediums(id),
    date        TEXT NOT NULL,
    month       TEXT NOT NULL,
    title       TEXT NOT NULL,
    notes       TEXT NOT NULL DEFAULT '',
    link        TEXT NOT NULL DEFAULT '',
    depth       INTEGER NOT NULL CHECK (depth BETWEEN 1 AND 5),
    created_at  TEXT,
    updated_at  TEXT
);
CREATE INDEX IF NOT EXISTS entries_month ON entries(month);
CREATE TABLE IF NOT EXISTS months (
    id           TEXT PRIMARY KEY,
    score        INTEGER,
    mediums      TEXT NOT NULL DEFAULT '[]',
    finalized_at TEXT
);
"""

# Same ids as the claude.ai artifact, so importing its export doesn't duplicate them.
DEFAULT_MEDIUMS = [
    ("books", "Books", "Technical and non-technical books"),
    ("algorithms", "Algorithm design problems", "Problems solved, patterns recognized"),
    ("work-challenges", "Challenges at work", "Technical problems faced and solved while working"),
    ("tech-methods", "Methods, technologies and libraries", "Techniques, tools, frameworks, libraries"),
    ("courses", "Courses, university and lectures", "Formal learning"),
    ("community", "Tech talks, community and collaboration", "Talks, meetups, open source, working with others"),
]


@dataclass(frozen=True)
class Field:
    api: str
    column: str
    kind: str = "plain"  # plain | bool | json


@dataclass(frozen=True)
class Table:
    name: str
    fields: tuple[Field, ...]

    def to_api(self, row: sqlite3.Row) -> dict:
        out = {"id": row["id"]}
        for f in self.fields:
            v = row[f.column]
            if f.kind == "bool":
                v = bool(v)
            elif f.kind == "json":
                v = json.loads(v)
            out[f.api] = v
        return out

    def to_row(self, data: dict) -> dict:
        row = {}
        for f in self.fields:
            v = data.get(f.api)
            if f.kind == "bool":
                v = int(bool(v))
            elif f.kind == "json":
                v = json.dumps(v)
            row[f.column] = v
        return row


TABLES = {
    "mediums": Table("mediums", (
        Field("name", "name"), Field("description", "description"), Field("weight", "weight"),
        Field("order", "sort_order"), Field("archived", "archived", "bool"), Field("createdAt", "created_at"),
    )),
    "entries": Table("entries", (
        Field("mediumId", "medium_id"), Field("date", "date"), Field("month", "month"),
        Field("title", "title"), Field("notes", "notes"), Field("link", "link"), Field("depth", "depth"),
        Field("createdAt", "created_at"), Field("updatedAt", "updated_at"),
    )),
    "months": Table("months", (
        Field("score", "score"), Field("mediums", "mediums", "json"), Field("finalizedAt", "finalized_at"),
    )),
}


def connect(path: str) -> sqlite3.Connection:
    # One connection per request, but FastAPI may open and close it on different
    # worker threads, so the same-thread check has to go.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = connect(path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM mediums").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO mediums (id, name, description, weight, sort_order, archived) VALUES (?, ?, ?, 1, ?, 0)",
                [(i, n, d, order) for order, (i, n, d) in enumerate(DEFAULT_MEDIUMS)],
            )
        conn.commit()
    finally:
        conn.close()


def list_all(conn, table: Table) -> list[dict]:
    return [table.to_api(r) for r in conn.execute(f"SELECT * FROM {table.name}")]


def get(conn, table: Table, doc_id: str) -> dict | None:
    row = conn.execute(f"SELECT * FROM {table.name} WHERE id = ?", (doc_id,)).fetchone()
    return table.to_api(row) if row else None


def upsert(conn, table: Table, doc_id: str, data: dict) -> None:
    row = table.to_row(data)
    cols = list(row)
    conn.execute(
        f"INSERT INTO {table.name} (id, {', '.join(cols)}) VALUES (?, {', '.join('?' * len(cols))}) "
        f"ON CONFLICT(id) DO UPDATE SET {', '.join(f'{c} = excluded.{c}' for c in cols)}",
        (doc_id, *row.values()),
    )
    conn.commit()


def delete(conn, table: Table, doc_id: str) -> None:
    conn.execute(f"DELETE FROM {table.name} WHERE id = ?", (doc_id,))
    conn.commit()
