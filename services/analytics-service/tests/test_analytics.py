from unittest.mock import Mock

import boto3
import pytest
from app.main import app
from app.repositories.dynamodb_repository import (
    DynamoDBRepository,
    RepositoryUnavailable,
    get_repository,
)
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import EndpointConnectionError
from botocore.stub import Stubber
from fastapi.testclient import TestClient


@pytest.fixture
def repository():
    return Mock(spec=DynamoDBRepository)


@pytest.fixture
def client(repository):
    app.dependency_overrides[get_repository] = lambda: repository
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_first_click(client, repository):
    repository.increment.return_value = 1
    response = client.post("/api/analytics/abc1234/click")
    assert response.status_code == 200
    assert response.json() == {"code": "abc1234", "click_count": 1}
    repository.increment.assert_called_once_with("abc1234")


def test_repeated_clicks(client, repository):
    repository.increment.side_effect = [1, 2, 3]
    for expected in [1, 2, 3]:
        response = client.post("/api/analytics/abc1234/click")
        assert response.status_code == 200
        assert response.json() == {"code": "abc1234", "click_count": expected}
    assert repository.increment.call_count == 3


def test_get_statistics(client, repository):
    repository.get.return_value = 5
    response = client.get("/api/analytics/abc1234")
    assert response.status_code == 200
    assert response.json() == {"code": "abc1234", "click_count": 5}
    repository.get.assert_called_once_with("abc1234")


def test_unknown_code(client, repository):
    repository.get.return_value = 0
    response = client.get("/api/analytics/unknown")
    assert response.status_code == 200
    assert response.json() == {"code": "unknown", "click_count": 0}


@pytest.mark.parametrize("operation", ["increment", "get"])
def test_storage_failure(client, repository, operation):
    getattr(repository, operation).side_effect = RepositoryUnavailable("AWS details")
    if operation == "increment":
        response = client.post("/api/analytics/abc1234/click")
    else:
        response = client.get("/api/analytics/abc1234")
    assert response.status_code == 503
    assert response.json() == {"detail": "Analytics storage is unavailable"}


@pytest.fixture
def dynamodb_client(monkeypatch):
    monkeypatch.delenv("ANALYTICS_TABLE_NAME", raising=False)
    return boto3.client(
        "dynamodb", region_name="us-east-1", config=Config(signature_version=UNSIGNED)
    )


def test_atomic_increment(dynamodb_client):
    repository = DynamoDBRepository(client=dynamodb_client)
    expected = {
        "TableName": "url_analytics",
        "Key": {"code": {"S": "abc1234"}},
        "UpdateExpression": "ADD click_count :increment",
        "ExpressionAttributeValues": {":increment": {"N": "1"}},
        "ReturnValues": "UPDATED_NEW",
    }
    with Stubber(dynamodb_client) as stubber:
        for count in [1, 2]:
            stubber.add_response(
                "update_item",
                {"Attributes": {"click_count": {"N": str(count)}}},
                expected,
            )
            assert repository.increment("abc1234") == count
        stubber.assert_no_pending_responses()


def test_read_existing_and_missing(dynamodb_client):
    repository = DynamoDBRepository(client=dynamodb_client)
    expected = {
        "TableName": "url_analytics",
        "Key": {"code": {"S": "abc1234"}},
        "ConsistentRead": True,
    }
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response(
            "get_item",
            {"Item": {"code": {"S": "abc1234"}, "click_count": {"N": "5"}}},
            expected,
        )
        stubber.add_response("get_item", {}, expected)
        assert repository.get("abc1234") == 5
        assert repository.get("abc1234") == 0
        stubber.assert_no_pending_responses()


@pytest.mark.parametrize("operation", ["increment", "get"])
def test_aws_errors_translated(dynamodb_client, operation):
    with Stubber(dynamodb_client) as stubber:
        stubber.add_client_error(
            "update_item" if operation == "increment" else "get_item",
            service_error_code="ProvisionedThroughputExceededException",
        )
        with pytest.raises(RepositoryUnavailable):
            getattr(DynamoDBRepository(client=dynamodb_client), operation)("abc1234")
        stubber.assert_no_pending_responses()


@pytest.mark.parametrize("operation", ["increment", "get"])
def test_connection_errors_translated(operation):
    client = Mock()
    method = client.update_item if operation == "increment" else client.get_item
    method.side_effect = EndpointConnectionError(endpoint_url="http://local")
    with pytest.raises(RepositoryUnavailable):
        getattr(DynamoDBRepository(client=client), operation)("abc1234")


@pytest.mark.parametrize("endpoint", [None, "http://localhost:8002"])
def test_configuration(monkeypatch, endpoint):
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("DYNAMODB_ENDPOINT_URL", raising=False)
    monkeypatch.setenv("ANALYTICS_TABLE_NAME", "custom_analytics")
    if endpoint:
        monkeypatch.setenv("DYNAMODB_ENDPOINT_URL", endpoint)
    factory = Mock()
    factory.return_value.get_item.return_value = {}
    monkeypatch.setattr("app.repositories.dynamodb_repository.boto3.client", factory)
    repository = DynamoDBRepository()
    expected = {"region_name": "us-east-1"}
    if endpoint:
        expected["endpoint_url"] = endpoint
    factory.assert_called_once_with("dynamodb", **expected)
    assert repository.get("abc1234") == 0
    assert (
        factory.return_value.get_item.call_args.kwargs["TableName"]
        == "custom_analytics"
    )


def test_initialization_failure(monkeypatch):
    factory = Mock(side_effect=EndpointConnectionError(endpoint_url="http://local"))
    monkeypatch.setattr("app.repositories.dynamodb_repository.boto3.client", factory)
    get_repository.cache_clear()
    try:
        with TestClient(app) as client:
            assert client.get("/health").status_code == 200
            response = client.get("/api/analytics/abc1234")
        assert response.status_code == 503
        assert response.json() == {"detail": "Analytics storage is unavailable"}
    finally:
        get_repository.cache_clear()
