import logging
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from app.repositories.dynamodb_repository import DynamoDBRepository, get_repository
from app.schemas.url import URLCreate, URLResponse
from app.services.analytics_client import (
    AnalyticsClient,
    AnalyticsStats,
    AnalyticsUnavailable,
    get_analytics_client,
)
from app.services.url_service import URLService

logger = logging.getLogger(__name__)
router = APIRouter()
Analytics = Annotated[AnalyticsClient, Depends(get_analytics_client)]
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
def redirect_url(
    code: str, repository: Repository, analytics: Analytics
) -> RedirectResponse:
    item = URLService(repository).get(code)
    if item is None:
        raise HTTPException(status_code=404, detail="Short URL not found")
    try:
        analytics.record_click(code)
    except AnalyticsUnavailable:
        logger.warning("Analytics click recording failed for code %s", code)
    return RedirectResponse(url=item["original_url"], status_code=302)


@router.get("/api/urls/{code}/stats", response_model=AnalyticsStats)
def get_statistics(
    code: str, repository: Repository, analytics: Analytics
) -> AnalyticsStats:
    if URLService(repository).get(code) is None:
        raise HTTPException(status_code=404, detail="Short URL not found")
    try:
        return analytics.get_stats(code)
    except AnalyticsUnavailable as exc:
        raise HTTPException(
            status_code=503, detail="Analytics service is unavailable"
        ) from exc
