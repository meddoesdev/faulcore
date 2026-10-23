"""Consistent public errors without exposing internal exception details."""

from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


def _response(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    if request_id is None:
        request_id = uuid4().hex
        request.state.request_id = request_id
    return JSONResponse(
        status_code=status_code,
        content={"code": code, "message": message, "request_id": request_id},
    )


async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle missing resources and explicitly raised HTTP errors."""
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return _response(request, exc.status_code, "http_error", message)


async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Keep validation errors structured without echoing rejected input."""
    return _response(request, 422, "validation_error", "Invalid request")


async def internal_error(request: Request, exc: Exception) -> JSONResponse:
    """Hide exception text and stack traces from clients."""
    return _response(request, 500, "internal_error", "Internal server error")


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, http_error)
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(Exception, internal_error)
