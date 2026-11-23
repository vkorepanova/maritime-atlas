from maritime_atlas.providers.aisstream import normalize_ais, vessel_features


def test_normalize_aisstream_position():
    message = {"MessageType": "PositionReport", "MetaData": {"MMSI": 123456789, "ShipName": "Test", "Latitude": 51.5, "Longitude": 1.1}, "Message": {"PositionReport": {"Sog": 12.4, "Cog": 86.7}}}
    result = normalize_ais(message, "2026-11-23T12:00:00+00:00")
    assert result["mmsi"] == "123456789"
    assert result["speed_knots"] == 12.4
    assert vessel_features({result["mmsi"]: result})["features"][0]["geometry"]["coordinates"] == [1.1, 51.5]
