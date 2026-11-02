from datetime import datetime
from unittest.mock import Mock

import boto3
import httpx
import pytest
from app.main import app
from app.repositories.dynamodb_repository import (
    CodeAlreadyExists,
    DynamoDBRepository,
    RepositoryUnavailable,
    get_repository,
)
from app.services.analytics_client import (
    AnalyticsClient,
    AnalyticsUnavailable,
    get_analytics_client,
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
def analytics():
    return Mock(spec=AnalyticsClient)


@pytest.fixture
def client(repository, analytics, monkeypatch):
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    app.dependency_overrides[get_repository] = lambda: repository
    app.dependency_overrides[get_analytics_client] = lambda: analytics
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_health(client, repository):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    repository.create.assert_not_called()
    repository.get.assert_not_called()


def test_create_url(client, repository):
    response = client.post("/api/urls", json={"url": "https://example.com"})
    assert response.status_code == 201
    body = response.json()
    code = body["code"]
    assert len(code) == 7
    assert code.isascii() and code.isalnum()
    assert body == {
        "code": code,
        "short_url": f"http://localhost:8000/r/{code}",
        "original_url": "https://example.com/",
    }
    repository.create.assert_called_once()
    item = repository.create.call_args.args[0]
    assert set(item) == {"code", "original_url", "created_at"}
    assert item["code"] == code
    assert item["original_url"] == body["original_url"]
    assert datetime.fromisoformat(item["created_at"]).utcoffset().total_seconds() == 0


def test_public_base_url(client, monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://short.example.com/")
    response = client.post("/api/urls", json={"url": "https://example.com/path"})
    assert response.status_code == 201
    body = response.json()
    assert body["short_url"] == f"https://short.example.com/r/{body['code']}"
    assert body["original_url"] == "https://example.com/path"


@pytest.mark.parametrize("url", ["not-a-url", "ftp://example.com", "", None])
def test_invalid_url(client, repository, url):
    assert client.post("/api/urls", json={"url": url}).status_code == 422
    repository.create.assert_not_called()


def test_missing_url(client):
    assert client.post("/api/urls", json={}).status_code == 422


def test_redirect(client, repository):
    repository.get.return_value = {"original_url": "https://example.com/path"}
    response = client.get("/r/abc1234", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/path"
    repository.get.assert_called_once_with("abc1234")


def test_unknown_code(client, repository):
    repository.get.return_value = None
    assert client.get("/r/unknown").status_code == 404


def test_collision_retries(client, repository, monkeypatch):
    choices = iter("aaaaaaabbbbbbb")
    monkeypatch.setattr(
        "app.services.url_service.secrets.choice", lambda _: next(choices)
    )
    repository.create.side_effect = [CodeAlreadyExists(), None]
    response = client.post("/api/urls", json={"url": "https://example.com"})
    assert response.status_code == 201
    assert response.json()["code"] == "bbbbbbb"
    assert [call.args[0]["code"] for call in repository.create.call_args_list] == [
        "aaaaaaa",
        "bbbbbbb",
    ]


def test_collision_exhaustion(client, repository):
    repository.create.side_effect = CodeAlreadyExists()
    response = client.post("/api/urls", json={"url": "https://example.com"})
    assert response.status_code == 503
    assert repository.create.call_count == 5
    assert response.json() == {"detail": "Unable to allocate a short code"}


@pytest.mark.parametrize("operation", ["create", "get"])
def test_repository_failure_returns_safe_error(client, repository, operation):
    getattr(repository, operation).side_effect = RepositoryUnavailable(
        "Internal AWS error"
    )
    if operation == "create":
        response = client.post("/api/urls", json={"url": "https://example.com"})
    else:
        response = client.get("/r/abc1234")
    assert response.status_code == 503
    assert response.json() == {"detail": "URL storage is unavailable"}


@pytest.fixture
def dynamodb_client():
    # Unsigned stubbed requests need no AWS credentials or credential discovery.
    return boto3.client(
        "dynamodb",
        region_name="us-east-1",
        config=Config(signature_version=UNSIGNED),
    )


def test_conditional_write_prevents_overwrite(dynamodb_client, monkeypatch):
    monkeypatch.delenv("URLS_TABLE_NAME", raising=False)
    repository = DynamoDBRepository(client=dynamodb_client)
    item = {
        "code": "abc1234",
        "original_url": "https://example.com/",
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    expected = {
        "TableName": "short_urls",
        "Item": {key: {"S": value} for key, value in item.items()},
        "ConditionExpression": "attribute_not_exists(#code)",
        "ExpressionAttributeNames": {"#code": "code"},
    }
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response("put_item", {}, expected)
        stubber.add_client_error(
            "put_item",
            service_error_code="ConditionalCheckFailedException",
            expected_params=expected,
        )
        repository.create(item)
        with pytest.raises(CodeAlreadyExists):
            repository.create(item)
        stubber.assert_no_pending_responses()


def test_repository_reads_existing_and_missing_items(dynamodb_client, monkeypatch):
    monkeypatch.delenv("URLS_TABLE_NAME", raising=False)
    repository = DynamoDBRepository(client=dynamodb_client)
    item = {"code": "abc1234", "original_url": "https://example.com/"}
    expected = {
        "TableName": "short_urls",
        "Key": {"code": {"S": "abc1234"}},
        "ConsistentRead": True,
    }
    with Stubber(dynamodb_client) as stubber:
        stubber.add_response(
            "get_item",
            {"Item": {key: {"S": value} for key, value in item.items()}},
            expected,
        )
        stubber.add_response("get_item", {}, expected)
        assert repository.get("abc1234") == item
        assert repository.get("abc1234") is None
        stubber.assert_no_pending_responses()


@pytest.mark.parametrize("operation", ["create", "get"])
def test_dynamodb_errors_are_translated(dynamodb_client, operation):
    repository = DynamoDBRepository(client=dynamodb_client)
    with Stubber(dynamodb_client) as stubber:
        stubber.add_client_error(
            "put_item" if operation == "create" else "get_item",
            service_error_code="ProvisionedThroughputExceededException",
        )
        with pytest.raises(RepositoryUnavailable):
            if operation == "create":
                repository.create({"code": "abc1234"})
            else:
                repository.get("abc1234")
        stubber.assert_no_pending_responses()


@pytest.mark.parametrize("operation", ["create", "get"])
def test_connection_errors_are_translated(operation):
    client = Mock()
    method = client.put_item if operation == "create" else client.get_item
    method.side_effect = EndpointConnectionError(endpoint_url="http://local")
    repository = DynamoDBRepository(client=client)
    with pytest.raises(RepositoryUnavailable):
        if operation == "create":
            repository.create({"code": "abc1234"})
        else:
            repository.get("abc1234")


@pytest.mark.parametrize("endpoint", [None, "http://localhost:8001"])
def test_dynamodb_configuration(monkeypatch, endpoint):
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("DYNAMODB_ENDPOINT_URL", raising=False)
    monkeypatch.setenv("URLS_TABLE_NAME", "custom_urls")
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
    repository.get("abc1234")
    assert factory.return_value.get_item.call_args.kwargs["TableName"] == "custom_urls"


def test_region_override(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "eu-west-1")
    monkeypatch.delenv("DYNAMODB_ENDPOINT_URL", raising=False)
    factory = Mock()
    monkeypatch.setattr("app.repositories.dynamodb_repository.boto3.client", factory)
    DynamoDBRepository()
    factory.assert_called_once_with("dynamodb", region_name="eu-west-1")


def test_client_creation_failure_returns_safe_error(monkeypatch):
    factory = Mock(side_effect=EndpointConnectionError(endpoint_url="http://local"))
    monkeypatch.setattr("app.repositories.dynamodb_repository.boto3.client", factory)
    get_repository.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post("/api/urls", json={"url": "https://example.com"})
        assert response.status_code == 503
        assert response.json() == {"detail": "URL storage is unavailable"}
    finally:
        get_repository.cache_clear()


def test_redirect_records_click(client, repository, analytics):
    repository.get.return_value = {"original_url": "https://example.com/"}
    response = client.get("/r/abc1234", follow_redirects=False)
    assert response.status_code == 302
    analytics.record_click.assert_called_once_with("abc1234")


def test_redirect_survives_analytics_failure(client, repository, analytics, caplog):
    repository.get.return_value = {"original_url": "https://example.com/"}
    analytics.record_click.side_effect = AnalyticsUnavailable("internal details")
    response = client.get("/r/abc1234", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/"
    assert "Analytics click recording failed" in caplog.text
    assert "internal details" not in response.text


def test_unknown_code_does_not_call_analytics(client, repository, analytics):
    repository.get.return_value = None
    assert client.get("/r/unknown").status_code == 404
    analytics.record_click.assert_not_called()


def test_stats(client, repository, analytics):
    repository.get.return_value = {"original_url": "https://example.com/"}
    analytics.get_stats.return_value = {"code": "abc1234", "click_count": 5}
    response = client.get("/api/urls/abc1234/stats")
    assert response.status_code == 200
    assert response.json() == {"code": "abc1234", "click_count": 5}
    analytics.get_stats.assert_called_once_with("abc1234")


def test_stats_unknown_code(client, repository, analytics):
    repository.get.return_value = None
    assert client.get("/api/urls/unknown/stats").status_code == 404
    analytics.get_stats.assert_not_called()


def test_stats_unavailable(client, repository, analytics):
    repository.get.return_value = {"original_url": "https://example.com/"}
    analytics.get_stats.side_effect = AnalyticsUnavailable("internal details")
    response = client.get("/api/urls/abc1234/stats")
    assert response.status_code == 503
    assert response.json() == {"detail": "Analytics service is unavailable"}


@pytest.mark.parametrize("failure", ["timeout", "connect", "http", "invalid_json"])
@pytest.mark.parametrize("endpoint", ["/r/abc1234", "/api/urls/abc1234/stats"])
def test_http_failures_at_client_boundary(
    client, repository, endpoint, failure, caplog
):
    repository.get.return_value = {"original_url": "https://example.com/"}

    def handler(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("slow analytics", request=request)
        if failure == "connect":
            raise httpx.ConnectError("unavailable analytics", request=request)
        if failure == "http":
            return httpx.Response(500, text="internal analytics error")
        return httpx.Response(200, text="not json")

    analytics = AnalyticsClient(
        "http://analytics", transport=httpx.MockTransport(handler)
    )
    app.dependency_overrides[get_analytics_client] = lambda: analytics
    response = client.get(endpoint, follow_redirects=False)
    assert response.status_code == (302 if endpoint.startswith("/r/") else 503)
    if endpoint.startswith("/r/"):
        assert "Analytics click recording failed" in caplog.text


@pytest.mark.parametrize("operation", ["record_click", "get_stats"])
def test_analytics_http_contract(operation):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"code": "abc1234", "click_count": 5})

    analytics = AnalyticsClient(
        "http://analytics/", timeout=0.15, transport=httpx.MockTransport(handler)
    )
    result = getattr(analytics, operation)("abc1234")
    assert result.code == "abc1234"
    assert result.click_count == 5
    assert len(requests) == 1
    request = requests[0]
    suffix = "/click" if operation == "record_click" else ""
    assert str(request.url) == f"http://analytics/api/analytics/abc1234{suffix}"
    assert request.method == ("POST" if operation == "record_click" else "GET")
    assert all(value == 0.15 for value in request.extensions["timeout"].values())


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"code": "wrong", "click_count": 5},
        {"code": "abc1234", "click_count": -1},
        {"code": "abc1234", "click_count": "not-an-integer"},
    ],
)
def test_bad_analytics_payload_is_controlled(payload):
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    with pytest.raises(AnalyticsUnavailable):
        AnalyticsClient("http://analytics", transport=transport).get_stats("abc1234")


def test_analytics_configuration(monkeypatch):
    monkeypatch.delenv("ANALYTICS_SERVICE_URL", raising=False)
    monkeypatch.delenv("ANALYTICS_TIMEOUT_SECONDS", raising=False)
    analytics = get_analytics_client()
    assert analytics.base_url == "http://localhost:8001"
    assert analytics.timeout == 0.3
    monkeypatch.setenv("ANALYTICS_SERVICE_URL", "http://analytics:8001/")
    monkeypatch.setenv("ANALYTICS_TIMEOUT_SECONDS", "0.2")
    analytics = get_analytics_client()
    assert analytics.base_url == "http://analytics:8001"
    assert analytics.timeout == 0.2


@pytest.mark.parametrize("timeout", ["invalid", "0", "-1", "inf", "nan"])
def test_invalid_timeout_uses_safe_default(monkeypatch, timeout):
    monkeypatch.setenv("ANALYTICS_TIMEOUT_SECONDS", timeout)
    assert get_analytics_client().timeout == 0.3


def test_request_logs_exclude_sensitive_values(client, caplog):
    response = client.get(
        "/health?token=private-query-value",
        headers={"Authorization": "Bearer private-token-value"},
    )
    assert response.status_code == 200
    assert '"event": "http_request"' in caplog.text
    assert "private-query-value" not in caplog.text
    assert "private-token-value" not in caplog.text
