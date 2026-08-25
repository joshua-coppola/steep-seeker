import requests

from core.connectors.osm_api import OSM


class FakeOSMResponse:
    def __init__(self, status_code=200, content=b""):
        self.status_code = status_code
        self.content = content


def test_get_returns_content_on_success(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        assert params == {"bbox": "-72.7,43.3,-72.6,43.4"}
        return FakeOSMResponse(200, b"<osm></osm>")

    monkeypatch.setattr(requests, "get", fake_get)

    result = OSM().get("-72.7,43.3,-72.6,43.4")

    assert result == b"<osm></osm>"


def test_get_returns_none_on_non_retryable_failure(monkeypatch):
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(1)
        return FakeOSMResponse(500)

    monkeypatch.setattr(requests, "get", fake_get)

    result = OSM().get("-72.7,43.3,-72.6,43.4")

    assert result is None
    assert len(calls) == 1


def test_get_retries_on_504_then_succeeds(monkeypatch):
    responses = [
        FakeOSMResponse(504),
        FakeOSMResponse(504),
        FakeOSMResponse(200, b"ok"),
    ]

    def fake_get(url, params=None, timeout=None):
        return responses.pop(0)

    monkeypatch.setattr(requests, "get", fake_get)

    result = OSM().get("-72.7,43.3,-72.6,43.4")

    assert result == b"ok"


def test_get_gives_up_after_three_504s(monkeypatch):
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(1)
        return FakeOSMResponse(504)

    monkeypatch.setattr(requests, "get", fake_get)

    result = OSM().get("-72.7,43.3,-72.6,43.4")

    assert result is None
    assert len(calls) == 3
