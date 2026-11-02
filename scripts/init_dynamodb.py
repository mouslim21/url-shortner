"""Create KATA tables in DynamoDB Local only; never use an AWS endpoint."""

import logging
import os
import time
from typing import Any
from urllib.parse import urlsplit

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

TABLE_NAMES = ("short_urls", "url_analytics")


def local_endpoint() -> str:
    endpoint = os.getenv("DYNAMODB_ENDPOINT_URL", "")
    parsed = urlsplit(endpoint)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"dynamodb-local", "localhost", "127.0.0.1", "::1"}
        or parsed.port is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("DYNAMODB_ENDPOINT_URL must be an explicit DynamoDB Local URL")
    return endpoint


def wait_until_ready(client: Any) -> None:
    for attempt in range(30):
        try:
            client.list_tables(Limit=1)
            return
        except (BotoCoreError, ClientError):
            if attempt == 29:
                raise
            time.sleep(1)


def initialize_tables() -> None:
    # Validate before creating a boto3 client or resolving any credentials.
    endpoint = local_endpoint()
    client = boto3.client(
        "dynamodb",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        endpoint_url=endpoint,
        config=Config(connect_timeout=1, read_timeout=2, retries={"max_attempts": 0}),
    )
    wait_until_ready(client)
    for table_name in TABLE_NAMES:
        try:
            client.create_table(
                TableName=table_name,
                KeySchema=[{"AttributeName": "code", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "code", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
            print(f"Created {table_name}", flush=True)
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "ResourceInUseException":
                raise
            print(f"Table {table_name} already exists", flush=True)
        client.get_waiter("table_exists").wait(
            TableName=table_name, WaiterConfig={"Delay": 1, "MaxAttempts": 30}
        )


if __name__ == "__main__":
    initialize_tables()
