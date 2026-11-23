from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from maritime_atlas.common import feature_collection, read_json


def create_app(root=None):
    base = Path(root) if root else (Path.cwd() if (Path.cwd() / "docs" / "index.html").is_file() else Path(__file__).resolve().parents[2])
    docs = base / "docs"
    app = FastAPI(title="Maritime Atlas API", version="0.1.0")

    @app.get("/api/health")
    def health():
        return {"mode": "local", "status": "ok", "layers": ["density", "flows", "vessels"]}

    @app.get("/api/{layer}")
    def geojson(layer: str):
        if layer not in ("density", "flows", "vessels"):
            return JSONResponse({"error": "Unknown layer"}, status_code=404)
        runtime = base / "runtime" / "vessels.geojson"
        path = runtime if layer == "vessels" and runtime.is_file() else docs / "data" / f"{layer}.geojson"
        return read_json(path) if path.is_file() else feature_collection()

    @app.get("/")
    def index():
        return FileResponse(docs / "index.html")

    app.mount("/", StaticFiles(directory=docs), name="site")
    return app


app = create_app()
