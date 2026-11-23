import pytest
from maritime_atlas.processing.flows import build_flows

ROUTES = {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[0,0],[1,1]]}, "properties": {"route_id": "test"}}]}


def test_unverified_routes_keep_null_tonnage():
    result = build_flows(ROUTES, [], 2025)
    assert result["features"][0]["properties"]["cargo_tonnes"] is None


def test_verified_requires_provenance():
    with pytest.raises(ValueError):
        build_flows(ROUTES, [{"route_id": "test", "year": "2025", "cargo_tonnes": "100"}], 2025)
    result = build_flows(ROUTES, [{"route_id": "test", "year": "2025", "cargo_tonnes": "100", "source_url": "https://example.org/source", "method": "observed"}], 2025)
    assert result["features"][0]["properties"]["cargo_tonnes"] == 100
