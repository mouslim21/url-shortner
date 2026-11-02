import secrets
import string
from datetime import UTC, datetime

from app.repositories.dynamodb_repository import CodeAlreadyExists, DynamoDBRepository

CODE_LENGTH = 7
MAX_ATTEMPTS = 5
CODE_ALPHABET = string.ascii_letters + string.digits


class ShortCodeExhausted(Exception):
    pass


class URLService:
    def __init__(self, repository: DynamoDBRepository) -> None:
        self.repository = repository

    def create(self, original_url: str) -> dict[str, str]:
        for _ in range(MAX_ATTEMPTS):
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
            item = {
                "code": code,
                "original_url": original_url,
                "created_at": datetime.now(UTC).isoformat(),
            }
            try:
                self.repository.create(item)
            except CodeAlreadyExists:
                continue
            return item
        raise ShortCodeExhausted()

    def get(self, code: str) -> dict[str, str] | None:
        return self.repository.get(code)
