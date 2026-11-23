from pathlib import Path
from maritime_atlas.common import read_json


def test_reference_corridors_are_unweighted_and_geographically_valid():
    root = Path(__file__).resolve().parents[1]
    data = read_json(root / 'data' / 'corridors.geojson')
    features = data['features']
    assert len(features) == 15
    assert len({f['properties']['route_id'] for f in features}) == 15
    for feature in features:
        geometry = feature['geometry']
        lines = [geometry['coordinates']] if geometry['type'] == 'LineString' else geometry['coordinates']
        for line in lines:
            for longitude, latitude in line:
                assert -180 <= longitude <= 180
                assert -90 <= latitude <= 90
