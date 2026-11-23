import json
import os
import tempfile
from pathlib import Path


def feature_collection(features=None):
    return {"type": "FeatureCollection", "features": features or []}


def write_json(path, payload):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent, delete=False) as stream:
        json.dump(payload, stream, ensure_ascii=False, separators=(",", ":"))
        temp = stream.name
    os.replace(temp, target)


def read_json(path):
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)
