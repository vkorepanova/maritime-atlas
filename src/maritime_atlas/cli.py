import argparse
import asyncio
import json
from pathlib import Path

from maritime_atlas.processing.density import density_from_csv
from maritime_atlas.processing.flows import flows_from_csv
from maritime_atlas.providers.aisstream import collect


def main():
    parser = argparse.ArgumentParser(prog="maritime-atlas")
    commands = parser.add_subparsers(dest="command", required=True)

    serve = commands.add_parser("serve", help="Run local API and map")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8020)

    track = commands.add_parser("track", help="Receive AISStream into a local GeoJSON snapshot")
    track.add_argument("--bbox", type=float, nargs=4, metavar=("S", "W", "N", "E"), required=True)
    track.add_argument("--minutes", type=float, default=10)
    track.add_argument("--output", default="runtime/vessels.geojson")
    track.add_argument("--observations", default="runtime/ais_observations.csv")

    density = commands.add_parser("build-density", help="Aggregate historical AIS positions by grid cell")
    density.add_argument("--csv", default="runtime/ais_observations.csv")
    density.add_argument("--output", default="docs/data/density.geojson")
    density.add_argument("--cell-size", type=float, default=1)

    flows = commands.add_parser("build-flows", help="Join verified route weights to reference corridors")
    flows.add_argument("--routes", default="data/corridors.geojson")
    flows.add_argument("--weights", default="data/flow_observations.csv")
    flows.add_argument("--output", default="docs/data/flows.geojson")
    flows.add_argument("--year", type=int, default=2025)

    raster = commands.add_parser("density-raster", help="Convert external GeoTIFF to an optimized web overlay")
    raster.add_argument("--input", required=True)
    raster.add_argument("--output", default="docs/data/density.png")
    raster.add_argument("--meta", default="docs/data/density_meta.json")
    raster.add_argument("--size", type=int, default=2048)
    raster.add_argument("--source-url")
    raster.add_argument("--period")

    args = parser.parse_args()
    if args.command == "serve":
        import uvicorn
        uvicorn.run("maritime_atlas.api:app", host=args.host, port=args.port)
    elif args.command == "track":
        print(json.dumps(asyncio.run(collect(args.bbox, args.minutes, args.output, args.observations)), ensure_ascii=False))
    elif args.command == "build-density":
        print(f"Density cells: {density_from_csv(args.csv, args.output, args.cell_size)}")
    elif args.command == "build-flows":
        print(f"Verified routes: {flows_from_csv(args.routes, args.weights, args.output, args.year)}")
    elif args.command == "density-raster":
        from maritime_atlas.processing.raster import raster_to_map
        print(raster_to_map(args.input, args.output, args.meta, args.size, args.source_url, args.period))


if __name__ == "__main__":
    main()
