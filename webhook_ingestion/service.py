from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .models import PolicyEvent
from .repository import EventRepository
from .security import verify_signature


@dataclass(frozen=True)
class WebhookResponse:
    status_code: int
    body: dict[str, object]


class WebhookService:
    def __init__(self, repository: EventRepository, secret: str) -> None:
        self.repository = repository
        self.secret = secret

    def handle(self, body: bytes, headers: Mapping[str, str]) -> WebhookResponse:
        signature = next(
            (value for key, value in headers.items() if key.lower() == "x-webhook-signature"),
            None,
        )
        if not verify_signature(self.secret, body, signature):
            return WebhookResponse(401, {"error": "invalid signature"})

        try:
            event = PolicyEvent.from_bytes(body)
        except (TypeError, ValueError) as exc:
            return WebhookResponse(400, {"error": str(exc)})

        result = self.repository.persist(event, body)
        return WebhookResponse(
            200,
            {
                "event_id": event.event_id,
                "duplicate": result.duplicate,
                "latest_updated": result.latest_updated,
            },
        )

