import os
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError


class CodeAlreadyExists(Exception):
    pass


class RepositoryUnavailable(Exception):
    pass


class DynamoDBRepository:
    def __init__(self, client: Any = None) -> None:
        self.table_name = os.getenv("URLS_TABLE_NAME", "short_urls")
        try:
            if client is None:
                options = {"region_name": os.getenv("AWS_REGION", "us-east-1")}
                endpoint = os.getenv("DYNAMODB_ENDPOINT_URL")
                if endpoint:
                    options["endpoint_url"] = endpoint
                client = boto3.client("dynamodb", **options)
            self.client = client
        except (BotoCoreError, ClientError) as exc:
            raise RepositoryUnavailable() from exc

    def create(self, item: dict[str, str]) -> None:
        try:
            self.client.put_item(
                TableName=self.table_name,
                Item={key: {"S": value} for key, value in item.items()},
                ConditionExpression="attribute_not_exists(#code)",
                ExpressionAttributeNames={"#code": "code"},
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise CodeAlreadyExists() from exc
            raise RepositoryUnavailable() from exc
        except BotoCoreError as exc:
            raise RepositoryUnavailable() from exc

    def get(self, code: str) -> dict[str, str] | None:
        try:
            response = self.client.get_item(
                TableName=self.table_name,
                Key={"code": {"S": code}},
                ConsistentRead=True,
            )
        except (BotoCoreError, ClientError) as exc:
            raise RepositoryUnavailable() from exc
        item = response.get("Item")
        if not item:
            return None
        return {key: value["S"] for key, value in item.items()}


@lru_cache
def get_repository() -> DynamoDBRepository:
    # Create the client on first use, never at import time or during health checks.
    return DynamoDBRepository()
