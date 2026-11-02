import json
import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.repositories.dynamodb_repository import RepositoryUnavailable
from app.routers.analytics import router

app = FastAPI(title="Analytics Service")
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
        status_code=503, content={"detail": "Analytics storage is unavailable"}
    )
