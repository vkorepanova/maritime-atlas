from maritime_atlas.processing.density import make_density


def test_unique_ship_hour_deduplicates_messages():
    records = [
        {"mmsi": "123", "timestamp_utc": "2026-11-23T12:00:00Z", "latitude": "50.2", "longitude": "2.2"},
        {"mmsi": "123", "timestamp_utc": "2026-11-23T12:40:00Z", "latitude": "50.2", "longitude": "2.2"},
        {"mmsi": "123", "timestamp_utc": "2026-11-23T13:01:00Z", "latitude": "50.2", "longitude": "2.2"},
        {"mmsi": "456", "timestamp_utc": "2026-11-23T12:02:00Z", "latitude": "50.2", "longitude": "2.2"},
    ]
    density = make_density(records, 1)
    assert len(density["features"]) == 1
    assert density["features"][0]["properties"] == {"ship_hours": 3, "vessels": 2, "positions": 4}
    assert density["metadata"]["period_end"] == "2026-11-23T13:01:00+00:00"
