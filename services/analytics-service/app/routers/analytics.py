from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.repositories.dynamodb_repository import DynamoDBRepository, get_repository
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/analytics")
Repository = Annotated[DynamoDBRepository, Depends(get_repository)]


class AnalyticsResponse(BaseModel):
    code: str
    click_count: int = Field(ge=0)


@router.post("/{code}/click", response_model=AnalyticsResponse)
def record_click(code: str, repository: Repository) -> AnalyticsResponse:
    count = AnalyticsService(repository).increment(code)
    return AnalyticsResponse(code=code, click_count=count)


@router.get("/{code}", response_model=AnalyticsResponse)
def get_statistics(code: str, repository: Repository) -> AnalyticsResponse:
    count = AnalyticsService(repository).get(code)
    return AnalyticsResponse(code=code, click_count=count)
