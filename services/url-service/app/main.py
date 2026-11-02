from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.repositories.dynamodb_repository import RepositoryUnavailable
from app.routers.urls import router
from app.services.url_service import ShortCodeExhausted

app = FastAPI(title="URL Service")
app.include_router(router)


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
