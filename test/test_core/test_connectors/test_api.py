import pytest
import requests
from core.connectors.api import get_elevation


class FakeResponse:
    def __init__(self, status_code=200, results=None):
        self.status_code = status_code
        self._results = results or []
        self.text = "fake response"

    def json(self):
        return {"results": self._results}


def test_get_elevation_success(monkeypatch):
    # Arrange
    nodes = [(-105.0, 40.0), (-106.0, 41.0)]
    fake_results = [
        {"elevation": 1600},
        {"elevation": 1700},
    ]

    def fake_get(url):
        return FakeResponse(200, fake_results)

    # Monkeypatch requests.get
    monkeypatch.setattr(requests, "get", fake_get)

    # Act
    result = get_elevation(nodes, spacing=100)

    # Assert
    assert len(result) == 2
    assert result[0] == [-105.0, 40.0, 1600]
    assert result[1] == [-106.0, 41.0, 1700]


def test_get_elevation_api_failure(monkeypatch):
    nodes = [(-105.0, 40.0)]

    def fake_get(url):
        return FakeResponse(status_code=500)

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(RuntimeError) as excinfo:
        get_elevation(nodes)

    assert "Elevation API call failed" in str(excinfo.value)


def test_get_elevation_empty_nodes():
    # Should just return empty list if input is empty
    assert get_elevation([]) == []
