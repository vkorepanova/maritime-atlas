import csv
import math
from copy import deepcopy

from maritime_atlas.common import read_json, write_json


def build_flows(routes, observations, year):
    by_id = {}
    for row in observations:
        if not row.get("cargo_tonnes") or str(row.get("year", "")) != str(year):
            continue
        route_id = str(row["route_id"]).strip()
        if route_id in by_id:
            raise ValueError(f"Duplicate route/year: {route_id}, {year}")
        tonnes = float(row["cargo_tonnes"])
        if not math.isfinite(tonnes) or tonnes < 0:
            raise ValueError(f"Negative cargo tonnes: {route_id}")
        if not row.get("source_url") or not row.get("method"):
            raise ValueError(f"Missing source or method for {route_id}")
        by_id[route_id] = {"cargo_tonnes": tonnes, "year": int(year), "source_url": row["source_url"], "method": row["method"], "status": "estimated_or_observed"}
    result = deepcopy(routes)
    known = set()
    for feature in result["features"]:
        item = feature["properties"]
        route_id = item["route_id"]
        known.add(route_id)
        item.update(by_id.get(route_id, {"cargo_tonnes": None, "year": int(year), "source_url": None, "method": None, "status": "tonnage_unverified"}))
    extra = set(by_id) - known
    if extra:
        raise ValueError(f"Unknown route IDs: {', '.join(sorted(extra))}")
    method = "searoute_network" if all(f["properties"].get("geometry_method") == "searoute_network" for f in result["features"]) else "schematic"
    result["metadata"] = {"kind": "corridors", "period": int(year), "source": "SeaRoute maritime graph; optional independently sourced tonnages" if method == "searoute_network" else "Schematic maritime corridors; optional independently sourced tonnages", "geometry_accuracy": "sea_network_unverified" if method == "searoute_network" else "illustrative", "note": "Sea-network routes are not AIS tracks or navigational routes; weights must refer to this exact origin, destination, and period."}
    return result


def flows_from_csv(routes_geojson, weights_csv, output_geojson, year):
    with open(weights_csv, newline="", encoding="utf-8") as source:
        result = build_flows(read_json(routes_geojson), csv.DictReader(source), year)
    write_json(output_geojson, result)
    return sum(f["properties"]["cargo_tonnes"] is not None for f in result["features"])
