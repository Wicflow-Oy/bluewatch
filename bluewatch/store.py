"""A small SQLite document store for contract objects (one table, JSON payloads).

Postgres-compatible in spirit: kind + id primary key, JSON text payload, timestamps.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from bluewatch.config import DATA_DIR

T = TypeVar("T", bound=BaseModel)

SCHEMA = """
CREATE TABLE IF NOT EXISTS docs (
  kind TEXT NOT NULL,
  id TEXT NOT NULL,
  payload TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (kind, id)
);
CREATE TABLE IF NOT EXISTS audit (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT NOT NULL,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  ref TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT ''
);
"""


class Store:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = str(path or (DATA_DIR / "bluewatch.db"))
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.executescript(SCHEMA)

    def put(self, kind: str, doc_id: str, obj: BaseModel) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            "INSERT INTO docs(kind, id, payload, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(kind, id) DO UPDATE SET payload = excluded.payload, updated_at = excluded.updated_at",
            (kind, doc_id, obj.model_dump_json(), now),
        )
        self.db.commit()

    def get(self, kind: str, doc_id: str, model: type[T]) -> T | None:
        row = self.db.execute("SELECT payload FROM docs WHERE kind = ? AND id = ?", (kind, doc_id)).fetchone()
        return model.model_validate_json(row[0]) if row else None

    def all(self, kind: str, model: type[T]) -> list[T]:
        rows = self.db.execute("SELECT payload FROM docs WHERE kind = ? ORDER BY id", (kind,)).fetchall()
        return [model.model_validate_json(r[0]) for r in rows]

    def audit(self, actor: str, action: str, ref: str, detail: str = "") -> None:
        """Append-only audit log: rows are never updated or deleted."""
        self.db.execute(
            "INSERT INTO audit(at, actor, action, ref, detail) VALUES (?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), actor, action, ref, detail),
        )
        self.db.commit()

    def audit_log(self, ref: str | None = None) -> list[tuple]:
        if ref is None:
            return self.db.execute("SELECT at, actor, action, ref, detail FROM audit ORDER BY seq").fetchall()
        return self.db.execute(
            "SELECT at, actor, action, ref, detail FROM audit WHERE ref = ? ORDER BY seq", (ref,)
        ).fetchall()
