from app.repositories.dynamodb_repository import DynamoDBRepository


class AnalyticsService:
    def __init__(self, repository: DynamoDBRepository) -> None:
        self.repository = repository

    def increment(self, code: str) -> int:
        return self.repository.increment(code)

    def get(self, code: str) -> int:
        return self.repository.get(code)
