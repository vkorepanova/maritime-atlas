import csv
import math
from collections import defaultdict
from datetime import datetime, timezone

from maritime_atlas.common import feature_collection, write_json


def _parse_utc(value):
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def make_density(rows, cell_degrees=1.0):
    if not 0 < cell_degrees <= 5:
        raise ValueError("cell_degrees must be in (0, 5]")
    bins = defaultdict(lambda: {"positions": 0, "hours": set(), "vessels": set()})
    first = last = None
    for row in rows:
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            continue
        stamp = _parse_utc(row["timestamp_utc"])
        vessel = str(row["mmsi"])
        lon_index = math.floor((min(lon, 179.999999) + 180) / cell_degrees)
        lat_index = math.floor((min(lat, 89.999999) + 90) / cell_degrees)
        slot = bins[(lon_index, lat_index)]
        slot["positions"] += 1
        slot["vessels"].add(vessel)
        slot["hours"].add((vessel, stamp.strftime("%Y-%m-%dT%H")))
        first = stamp if first is None else min(first, stamp)
        last = stamp if last is None else max(last, stamp)
    features = []
    for (x, y), item in sorted(bins.items()):
        west = -180 + x * cell_degrees
        south = -90 + y * cell_degrees
        east = min(west + cell_degrees, 180)
        north = min(south + cell_degrees, 90)
        features.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[west,south],[east,south],[east,north],[west,north],[west,south]]]},
            "properties": {"ship_hours": len(item["hours"]), "vessels": len(item["vessels"]), "positions": item["positions"]}
        })
    output = feature_collection(features)
    output["metadata"] = {
        "kind": "ais_grid", "source": "AIS observations supplied by user",
        "metric": "unique MMSI-hour per grid cell", "unit": "ship_hours",
        "cell_degrees": cell_degrees,
        "period_start": first.isoformat() if first else None,
        "period_end": last.isoformat() if last else None,
        "spatial_coverage": "limited to collected AIS positions"
    }
    return output


def density_from_csv(input_csv, output_geojson, cell_degrees=1.0):
    with open(input_csv, newline="", encoding="utf-8") as source:
        data = make_density(csv.DictReader(source), cell_degrees)
    write_json(output_geojson, data)
    return len(data["features"])
