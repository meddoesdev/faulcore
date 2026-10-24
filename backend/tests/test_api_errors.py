"""Check the public error boundary before API routes are introduced."""

import asyncio
import json

from fastapi import Request
from starlette.exceptions import HTTPException

from backend.api.app import app
from backend.api.errors import http_error, internal_error


def _request() -> Request:
    return Request({"type": "http", "method": "GET", "path": "/", "headers": []})


def test_app_has_structured_error_handlers() -> None:
    assert HTTPException in app.exception_handlers
    assert Exception in app.exception_handlers


def test_unknown_route_returns_structured_json() -> None:
    messages: list[dict] = []

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict) -> None:
        messages.append(message)

    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": "GET", "scheme": "http", "path": "/unknown",
        "raw_path": b"/unknown", "query_string": b"", "root_path": "",
        "headers": [], "server": ("localhost", 80), "client": ("127.0.0.1", 1234),
    }
    asyncio.run(app(scope, receive, send))
    assert messages[0]["status"] == 404
    payload = json.loads(messages[1]["body"])
    assert payload["code"] == "http_error"
    assert payload["request_id"]


def test_http_error_contains_request_id() -> None:
    response = asyncio.run(http_error(_request(), HTTPException(status_code=404, detail="Not found")))
    assert response.status_code == 404
    assert b'"code":"http_error"' in response.body
    assert b'"request_id":' in response.body


def test_internal_error_hides_exception_text() -> None:
    response = asyncio.run(internal_error(_request(), RuntimeError("private detail")))
    assert response.status_code == 500
    assert b"private detail" not in response.body
    assert b'"code":"internal_error"' in response.body
