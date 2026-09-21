from __future__ import annotations

import json
import os

import azure.functions as func

from webhook_ingestion.repository import EventRepository
from webhook_ingestion.service import WebhookService

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(route="policy-events", methods=["POST"])
def policy_events(request: func.HttpRequest) -> func.HttpResponse:
    secret = os.environ.get("WEBHOOK_SECRET", "")
    database = os.environ.get("WEBHOOK_DATABASE", "webhook_events.db")
    if not secret:
        return func.HttpResponse(
            json.dumps({"error": "WEBHOOK_SECRET is not configured"}),
            status_code=500,
            mimetype="application/json",
        )

    result = WebhookService(EventRepository(database), secret).handle(
        request.get_body(), dict(request.headers)
    )
    return func.HttpResponse(
        json.dumps(result.body),
        status_code=result.status_code,
        mimetype="application/json",
    )

