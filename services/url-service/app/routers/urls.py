import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from app.repositories.dynamodb_repository import DynamoDBRepository, get_repository
from app.schemas.url import URLCreate, URLResponse
from app.services.url_service import URLService

router = APIRouter()
Repository = Annotated[DynamoDBRepository, Depends(get_repository)]


@router.post("/api/urls", response_model=URLResponse, status_code=201)
def create_url(payload: URLCreate, repository: Repository) -> URLResponse:
    item = URLService(repository).create(str(payload.url))
    base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
    return URLResponse(
        code=item["code"],
        short_url=f"{base_url}/r/{item['code']}",
        original_url=item["original_url"],
    )


@router.get("/r/{code}")
def redirect_url(code: str, repository: Repository) -> RedirectResponse:
    item = URLService(repository).get(code)
    if item is None:
        raise HTTPException(status_code=404, detail="Short URL not found")
    return RedirectResponse(url=item["original_url"], status_code=302)
