import asyncio
import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import websockets
from dotenv import load_dotenv
from maritime_atlas.common import feature_collection, write_json


def normalize_ais(message, received_at=None):
    if message.get("MessageType") not in ("PositionReport", "StandardClassBPositionReport", "ExtendedClassBPositionReport"):
        return None
    metadata = message.get("MetaData") or {}
    report = (message.get("Message") or {}).get(message["MessageType"]) or {}
    position = report.get("Position") or {}
    latitude = metadata.get("latitude", metadata.get("Latitude", position.get("latitude", position.get("Latitude"))))
    longitude = metadata.get("longitude", metadata.get("Longitude", position.get("longitude", position.get("Longitude"))))
    mmsi = metadata.get("MMSI") or report.get("UserID")
    if mmsi is None or latitude is None or longitude is None:
        return None
    lat, lon = float(latitude), float(longitude)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    timestamp = received_at or datetime.now(timezone.utc).isoformat()
    return {
        "mmsi": str(mmsi), "name": str(metadata.get("ShipName") or "Без названия").strip(),
        "latitude": lat, "longitude": lon,
        "speed_knots": report.get("Sog"), "course_degrees": report.get("Cog"),
        "timestamp_utc": timestamp, "source": "AISStream", "status": "observed_position"
    }


def vessel_features(positions):
    return feature_collection([{
        "type": "Feature", "geometry": {"type": "Point", "coordinates": [p["longitude"], p["latitude"]]},
        "properties": {k: v for k, v in p.items() if k not in ("latitude", "longitude")}
    } for p in positions.values()])


async def collect(bbox, minutes, output, observations_path):
    load_dotenv()
    api_key = os.getenv("AISSTREAM_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("AISSTREAM_API_KEY not set in .env")
    south, west, north, east = map(float, bbox)
    if not (-90 <= south < north <= 90 and -180 <= west < east <= 180):
        raise ValueError("bbox format: SOUTH WEST NORTH EAST, no antimeridian crossing")
    if minutes <= 0:
        raise ValueError("minutes must be positive")
    subscription = {"APIKey": api_key, "BoundingBoxes": [[[south, west], [north, east]]], "FilterMessageTypes": ["PositionReport", "StandardClassBPositionReport", "ExtendedClassBPositionReport"]}
    path = Path(observations_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existed = path.exists() and path.stat().st_size > 0
    positions = {}
    count = 0
    deadline = time.monotonic() + minutes * 60
    delay = 1
    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["mmsi", "timestamp_utc", "latitude", "longitude", "speed_knots", "course_degrees"])
        if not existed:
            writer.writeheader()
        while time.monotonic() < deadline:
            try:
                async with websockets.connect("wss://stream.aisstream.io/v0/stream", compression="deflate", max_size=4 * 1024 * 1024, ping_interval=20) as socket:
                    await socket.send(json.dumps(subscription))
                    delay = 1
                    while time.monotonic() < deadline:
                        try:
                            raw = await asyncio.wait_for(socket.recv(), timeout=min(10, max(0.1, deadline - time.monotonic())))
                        except asyncio.TimeoutError:
                            write_json(output, vessel_features(positions))
                            continue
                        event = json.loads(raw)
                        vessel = normalize_ais(event)
                        if vessel is None:
                            continue
                        positions[vessel["mmsi"]] = vessel
                        writer.writerow({k: vessel[k] for k in writer.fieldnames})
                        count += 1
                        if count % 25 == 0:
                            file.flush()
                            write_json(output, vessel_features(positions))
            except (websockets.exceptions.WebSocketException, OSError, asyncio.TimeoutError):
                if time.monotonic() >= deadline:
                    break
                await asyncio.sleep(min(delay, max(0, deadline - time.monotonic())))
                delay = min(delay * 2, 30)
    write_json(output, vessel_features(positions))
    return {"messages": count, "unique_vessels": len(positions), "output": str(output)}
