import logging
import math
import os
from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AnalyticsUnavailable(Exception):
    pass


class AnalyticsStats(BaseModel):
    code: str
    click_count: int = Field(ge=0, strict=True)


class AnalyticsClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 0.3,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.transport = transport

    def _request(self, method: str, code: str, suffix: str = "") -> AnalyticsStats:
        path = f"{self.base_url}/api/analytics/{quote(code, safe='')}{suffix}"
        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                response = client.request(method, path)
                response.raise_for_status()
                stats = AnalyticsStats.model_validate(response.json())
                if stats.code != code:
                    raise ValueError("Unexpected analytics code")
                return stats
        except (httpx.HTTPError, ValueError) as exc:
            raise AnalyticsUnavailable() from exc

    def record_click(self, code: str) -> AnalyticsStats:
        return self._request("POST", code, "/click")

    def get_stats(self, code: str) -> AnalyticsStats:
        return self._request("GET", code)


def get_analytics_client() -> AnalyticsClient:
    try:
        timeout = float(os.getenv("ANALYTICS_TIMEOUT_SECONDS", "0.3"))
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Timeout must be positive and finite")
    except ValueError:
        logger.warning("Invalid analytics timeout; using 0.3 seconds")
        timeout = 0.3
    return AnalyticsClient(
        os.getenv("ANALYTICS_SERVICE_URL", "http://localhost:8001"), timeout=timeout
    )
