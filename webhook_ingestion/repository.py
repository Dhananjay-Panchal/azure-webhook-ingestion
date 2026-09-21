from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .models import PolicyEvent


@dataclass(frozen=True)
class PersistResult:
    duplicate: bool
    latest_updated: bool


class EventRepository:
    """SQLite reference adapter; replace with PostgreSQL in a cloud deployment."""

    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS raw_webhook_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    policy_id TEXT NOT NULL,
                    occurred_at_utc TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    body_sha256 TEXT NOT NULL,
                    received_at_utc TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS policy_status_latest (
                    policy_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    occurred_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        return connection

    def persist(self, event: PolicyEvent, raw_body: bytes) -> PersistResult:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            inserted = connection.execute(
                """
                INSERT INTO raw_webhook_events VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_id) DO NOTHING
                """,
                (
                    event.event_id,
                    event.event_type,
                    event.policy_id,
                    event.occurred_at_utc,
                    json.dumps(event.payload, sort_keys=True),
                    hashlib.sha256(raw_body).hexdigest(),
                    now,
                ),
            ).rowcount
            if inserted == 0:
                return PersistResult(duplicate=True, latest_updated=False)

            current = connection.execute(
                "SELECT occurred_at_utc FROM policy_status_latest WHERE policy_id = ?",
                (event.policy_id,),
            ).fetchone()
            latest_updated = current is None or event.occurred_at_utc >= current["occurred_at_utc"]
            if latest_updated:
                connection.execute(
                    """
                    INSERT INTO policy_status_latest VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(policy_id) DO UPDATE SET
                        status = excluded.status,
                        event_id = excluded.event_id,
                        occurred_at_utc = excluded.occurred_at_utc,
                        updated_at_utc = excluded.updated_at_utc
                    """,
                    (
                        event.policy_id,
                        event.status,
                        event.event_id,
                        event.occurred_at_utc,
                        now,
                    ),
                )
        return PersistResult(duplicate=False, latest_updated=latest_updated)

    def raw_event_count(self) -> int:
        with self._connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM raw_webhook_events").fetchone()[0])

    def latest_status(self, policy_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status FROM policy_status_latest WHERE policy_id = ?",
                (policy_id,),
            ).fetchone()
        return row["status"] if row else None

