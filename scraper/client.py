"""HTTP client for the TomTom Traffic Index live endpoint."""

from __future__ import annotations

import logging
import time

import requests

from .config import Settings

LOGGER = logging.getLogger(__name__)

LIVE_TRAFFIC_PATH = "/traffic-index/api/live-traffic.json"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class TomTomError(RuntimeError):
    """Raised when TomTom data cannot be fetched or parsed."""


class TrafficIndexClient:
    def __init__(self, settings: Settings, session: requests.Session | None = None):
        self._settings = settings
        self._session = session or requests.Session()
        self._session.headers.update(
            {
                "User-Agent": settings.user_agent,
                "Accept": "application/json",
                "Referer": f"{settings.base_url}/traffic-index/",
            }
        )

    @property
    def live_traffic_url(self) -> str:
        return f"{self._settings.base_url}{LIVE_TRAFFIC_PATH}"

    def fetch_live_traffic(self, region_id: str) -> dict:
        params = {"city": region_id}
        last_error: Exception | None = None

        for attempt in range(1, self._settings.retries + 1):
            try:
                response = self._session.get(
                    self.live_traffic_url,
                    params=params,
                    timeout=self._settings.timeout,
                )
                if response.status_code == 404:
                    raise TomTomError(f"region '{region_id}' was not found (HTTP 404)")
                if response.status_code in RETRYABLE_STATUS:
                    raise requests.HTTPError(
                        f"retryable HTTP {response.status_code}", response=response
                    )
                response.raise_for_status()
                payload = response.json()
                self._validate(payload, region_id)
                return payload
            except TomTomError:
                raise
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt >= self._settings.retries:
                    break
                delay = min(2 ** (attempt - 1), 30)
                LOGGER.warning(
                    "fetch failed for %s (attempt %d/%d): %s; retrying in %ss",
                    region_id,
                    attempt,
                    self._settings.retries,
                    exc,
                    delay,
                )
                time.sleep(delay)

        raise TomTomError(
            f"failed to fetch live traffic for '{region_id}': {last_error}"
        ) from last_error

    @staticmethod
    def _validate(payload: object, region_id: str) -> None:
        if not isinstance(payload, dict):
            raise ValueError("response is not a JSON object")
        data = payload.get("data")
        if not isinstance(data, list) or not data:
            raise ValueError("response does not contain a non-empty 'data' list")
        returned_region = (payload.get("region") or {}).get("id")
        if returned_region and returned_region != region_id:
            LOGGER.warning(
                "requested region %s but API returned %s", region_id, returned_region
            )
