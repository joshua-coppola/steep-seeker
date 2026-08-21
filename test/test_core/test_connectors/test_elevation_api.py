import pytest
import requests
from core.connectors import elevation_api
from core.connectors.elevation_api import Elevation
from test.test_core.conftest import FakeResponse


def test_get_elevation_success(monkeypatch, cache_db_path):
    monkeypatch.setattr(elevation_api, "CACHE_DB_PATH", cache_db_path)

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
    result = Elevation().get(nodes, spacing=100)

    # Assert
    assert len(result) == 2
    assert result[0] == [-105.0, 40.0, 1600]
    assert result[1] == [-106.0, 41.0, 1700]


def test_get_elevation_api_failure(monkeypatch, cache_db_path):
    monkeypatch.setattr(elevation_api, "CACHE_DB_PATH", cache_db_path)

    nodes = [(-105.1, 40.0)]

    def fake_get(url):
        return FakeResponse(status_code=500)

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(RuntimeError) as excinfo:
        Elevation().get(nodes)

    assert "Elevation API call failed" in str(excinfo.value)


def test_get_elevation_empty_nodes():
    # Should just return empty list if input is empty
    assert Elevation().get([]) == []


def test_get_elevation_rounds_before_cache_lookup(monkeypatch, cache_db_path):
    monkeypatch.setattr(elevation_api, "CACHE_DB_PATH", cache_db_path)

    def fake_get(url):
        return FakeResponse(200, [{"elevation": 1600}])

    monkeypatch.setattr(requests, "get", fake_get)

    # Seed the cache with a canonical, 6-decimal-place point.
    Elevation().get([(-105.123456, 40.654321)])

    # A point differing only by float noise past the 6th decimal place --
    # the kind reprojection/resampling math produces for what is really the
    # same point -- must still round to the cached point and hit the cache
    # rather than re-querying the API.
    def fail_get(url):
        raise AssertionError("should not hit the API on a cache hit")

    monkeypatch.setattr(requests, "get", fail_get)

    result = Elevation().get([(-105.123456 + 3e-9, 40.654321 - 4e-9)])

    assert result == [[-105.123456, 40.654321, 1600]]
