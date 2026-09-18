import requests

from core.connectors.osm_api import OSM


class FakeOSMResponse:
    def __init__(self, status_code=200, content=b""):
        self.status_code = status_code
        self.content = content


def test_get_returns_content_on_success(monkeypatch):
    def fake_post(url, data=None, timeout=None, headers=None):
        assert url == OSM.BASE_URL
        assert headers == OSM.HEADERS
        # bbox reordered from min_lon,min_lat,max_lon,max_lat to Overpass
        # QL's south,west,north,east
        assert "(43.3,-72.7,43.4,-72.6)" in data["data"]
        assert 'way["piste:type"]' in data["data"]
        assert 'way["aerialway"]' in data["data"]
        assert 'relation["piste:type"]' in data["data"]
        return FakeOSMResponse(200, b"<osm></osm>")

    monkeypatch.setattr(requests, "post", fake_post)

    result = OSM().get("-72.7,43.3,-72.6,43.4")

    assert result == b"<osm></osm>"


def test_get_returns_none_on_non_retryable_failure(monkeypatch):
    calls = []

    def fake_post(url, data=None, timeout=None, headers=None):
        calls.append(1)
        return FakeOSMResponse(500)

    monkeypatch.setattr(requests, "post", fake_post)

    result = OSM().get("-72.7,43.3,-72.6,43.4")

    assert result is None
    assert len(calls) == 1


def test_get_retries_on_504_then_succeeds(monkeypatch):
    responses = [
        FakeOSMResponse(504),
        FakeOSMResponse(504),
        FakeOSMResponse(200, b"ok"),
    ]

    def fake_post(url, data=None, timeout=None, headers=None):
        return responses.pop(0)

    monkeypatch.setattr(requests, "post", fake_post)

    result = OSM().get("-72.7,43.3,-72.6,43.4")

    assert result == b"ok"


def test_get_gives_up_after_three_504s(monkeypatch):
    calls = []

    def fake_post(url, data=None, timeout=None, headers=None):
        calls.append(1)
        return FakeOSMResponse(504)

    monkeypatch.setattr(requests, "post", fake_post)

    result = OSM().get("-72.7,43.3,-72.6,43.4")

    assert result is None
    assert len(calls) == 3
