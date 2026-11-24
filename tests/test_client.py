import pytest
import requests

from scraper.client import TomTomError, TrafficIndexClient
from scraper.config import Settings


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.headers = {}
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        return self.responses.pop(0)


def _settings(**overrides):
    values = dict(
        base_url="https://www.tomtom.com",
        regions=("IDN_jakarta_new",),
        data_dir="data",
        timeout=5.0,
        retries=3,
        request_delay=0.0,
        user_agent="test-agent",
    )
    values.update(overrides)
    return Settings(**values)


def test_fetch_returns_payload(monkeypatch):
    monkeypatch.setattr("scraper.client.time.sleep", lambda _: None)
    payload = {"region": {"id": "IDN_jakarta_new"}, "data": [{"updateTime": 1}]}
    session = FakeSession([FakeResponse(200, payload)])

    result = TrafficIndexClient(_settings(), session).fetch_live_traffic("IDN_jakarta_new")

    assert result == payload
    assert session.calls[0]["url"] == "https://www.tomtom.com/traffic-index/api/live-traffic.json"
    assert session.calls[0]["params"] == {"city": "IDN_jakarta_new"}
    assert session.calls[0]["timeout"] == 5.0


def test_fetch_retries_on_server_error(monkeypatch):
    sleeps = []
    monkeypatch.setattr("scraper.client.time.sleep", sleeps.append)
    payload = {"region": {"id": "IDN_jakarta_new"}, "data": [{"updateTime": 1}]}
    session = FakeSession([FakeResponse(503), FakeResponse(200, payload)])

    result = TrafficIndexClient(_settings(), session).fetch_live_traffic("IDN_jakarta_new")

    assert result == payload
    assert len(session.calls) == 2
    assert sleeps == [1]


def test_fetch_raises_on_unknown_region(monkeypatch):
    monkeypatch.setattr("scraper.client.time.sleep", lambda _: None)
    session = FakeSession([FakeResponse(404)])

    with pytest.raises(TomTomError, match="not found"):
        TrafficIndexClient(_settings(), session).fetch_live_traffic("IDN_unknown_new")


def test_fetch_rejects_empty_data(monkeypatch):
    monkeypatch.setattr("scraper.client.time.sleep", lambda _: None)
    session = FakeSession(
        [FakeResponse(200, {"region": {}, "data": []}) for _ in range(3)]
    )

    with pytest.raises(TomTomError, match="failed to fetch"):
        TrafficIndexClient(_settings(), session).fetch_live_traffic("IDN_jakarta_new")
