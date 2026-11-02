from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.repositories.dynamodb_repository import RepositoryUnavailable
from app.routers.analytics import router

app = FastAPI(title="Analytics Service")
app.include_router(router)


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
