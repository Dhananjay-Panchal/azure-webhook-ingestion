from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class PolicyEvent:
    event_id: str
    event_type: str
    occurred_at_utc: str
    policy_id: str
    status: str
    payload: dict[str, Any]

    @classmethod
    def from_bytes(cls, body: bytes) -> PolicyEvent:
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("request body must be valid UTF-8 JSON") from exc

        required = ["event_id", "event_type", "occurred_at", "policy_id", "status"]
        missing = [field for field in required if not str(payload.get(field, "")).strip()]
        if missing:
            raise ValueError(f"missing required fields: {', '.join(missing)}")

        occurred_at = datetime.fromisoformat(payload["occurred_at"])
        if occurred_at.tzinfo is None:
            raise ValueError("occurred_at must include a timezone")

        return cls(
            event_id=str(payload["event_id"]).strip(),
            event_type=str(payload["event_type"]).strip(),
            occurred_at_utc=occurred_at.astimezone(UTC).isoformat(),
            policy_id=str(payload["policy_id"]).strip(),
            status=str(payload["status"]).strip().lower(),
            payload=payload,
        )
