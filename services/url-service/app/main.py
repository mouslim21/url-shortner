import json
import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.repositories.dynamodb_repository import RepositoryUnavailable
from app.routers.urls import router
from app.services.url_service import ShortCodeExhausted

app = FastAPI(title="URL Service")
app.include_router(router)

logging.basicConfig(level=logging.INFO, format="%(message)s")
request_logger = logging.getLogger("application.requests")
request_logger.setLevel(logging.INFO)


@app.middleware("http")
async def log_request(request: Request, call_next):
    started = time.monotonic()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        request_logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "method": request.method,
                    "route": getattr(route, "path", "unmatched"),
                    "status": status,
                    "duration_ms": round((time.monotonic() - started) * 1000, 2),
                }
            )
        )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.exception_handler(RepositoryUnavailable)
async def storage_unavailable(
    request: Request, exc: RepositoryUnavailable
) -> JSONResponse:
    return JSONResponse(
        status_code=503, content={"detail": "URL storage is unavailable"}
    )


@app.exception_handler(ShortCodeExhausted)
async def short_code_exhausted(
    request: Request, exc: ShortCodeExhausted
) -> JSONResponse:
    return JSONResponse(
        status_code=503, content={"detail": "Unable to allocate a short code"}
    )
