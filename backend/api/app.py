"""FastAPI application shell; routes follow shared contract review."""

from fastapi import FastAPI

from backend.api.errors import install_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="FaultCore RecallScope")
    install_error_handlers(app)
    return app


app = create_app()
