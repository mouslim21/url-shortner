import os
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError


class RepositoryUnavailable(Exception):
    pass


class DynamoDBRepository:
    def __init__(self, client: Any = None) -> None:
        self.table_name = os.getenv("ANALYTICS_TABLE_NAME", "url_analytics")
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

    def increment(self, code: str) -> int:
        try:
            response = self.client.update_item(
                TableName=self.table_name,
                Key={"code": {"S": code}},
                UpdateExpression="ADD click_count :increment",
                ExpressionAttributeValues={":increment": {"N": "1"}},
                ReturnValues="UPDATED_NEW",
            )
        except (BotoCoreError, ClientError) as exc:
            raise RepositoryUnavailable() from exc
        return int(response["Attributes"]["click_count"]["N"])

    def get(self, code: str) -> int:
        try:
            response = self.client.get_item(
                TableName=self.table_name,
                Key={"code": {"S": code}},
                ConsistentRead=True,
            )
        except (BotoCoreError, ClientError) as exc:
            raise RepositoryUnavailable() from exc
        item = response.get("Item")
        return int(item["click_count"]["N"]) if item else 0


@lru_cache
def get_repository() -> DynamoDBRepository:
    return DynamoDBRepository()
