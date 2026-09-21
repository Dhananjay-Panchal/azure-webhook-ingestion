from __future__ import annotations

import json

from webhook_ingestion.repository import EventRepository
from webhook_ingestion.security import sign
from webhook_ingestion.service import WebhookService


def payload(event_id: str, status: str, occurred_at: str) -> bytes:
    return json.dumps(
        {
            "event_id": event_id,
            "event_type": "policy.status.changed",
            "occurred_at": occurred_at,
            "policy_id": "POL-100",
            "status": status,
            "source": "synthetic-crm",
        },
        separators=(",", ":"),
    ).encode()


def headers(secret: str, body: bytes) -> dict[str, str]:
    return {"X-Webhook-Signature": sign(secret, body)}


def test_rejects_invalid_signature(tmp_path) -> None:
    service = WebhookService(EventRepository(tmp_path / "events.db"), "secret")
    body = payload("evt-1", "active", "2026-01-02T00:00:00Z")

    response = service.handle(body, {"X-Webhook-Signature": "sha256=bad"})

    assert response.status_code == 401


def test_deduplicates_and_preserves_latest_status(tmp_path) -> None:
    repository = EventRepository(tmp_path / "events.db")
    service = WebhookService(repository, "secret")
    newest = payload("evt-new", "active", "2026-01-03T00:00:00Z")
    older = payload("evt-old", "pending", "2026-01-01T00:00:00Z")

    first = service.handle(newest, headers("secret", newest))
    duplicate = service.handle(newest, headers("secret", newest))
    late_arrival = service.handle(older, headers("secret", older))

    assert first.body["latest_updated"] is True
    assert duplicate.body["duplicate"] is True
    assert late_arrival.body["latest_updated"] is False
    assert repository.raw_event_count() == 2
    assert repository.latest_status("POL-100") == "active"


def test_rejects_missing_fields(tmp_path) -> None:
    repository = EventRepository(tmp_path / "events.db")
    service = WebhookService(repository, "secret")
    body = b'{"event_id":"evt-1"}'

    response = service.handle(body, headers("secret", body))

    assert response.status_code == 400
    assert "missing required fields" in str(response.body["error"])

