from pathlib import Path

from maritime_atlas.common import write_json


def raster_to_map(input_tif, output_png, output_metadata, size=2048, source_url=None, period=None):
    import numpy as np
    import rasterio
    from PIL import Image
    from rasterio.enums import Resampling
    from rasterio.transform import from_bounds
    from rasterio.warp import reproject

    if size < 256 or size > 4096:
        raise ValueError("size must be between 256 and 4096")
    world = 20037508.342789244
    destination = np.full((size, size), np.nan, dtype=np.float32)
    with rasterio.open(input_tif) as source:
        if source.crs is None:
            raise ValueError("GeoTIFF has no coordinate reference system")
        reproject(
            source=rasterio.band(source, 1), destination=destination,
            src_transform=source.transform, src_crs=source.crs,
            src_nodata=source.nodata,
            dst_transform=from_bounds(-world, -world, world, world, size, size),
            dst_crs="EPSG:3857", dst_nodata=np.nan, resampling=Resampling.average
        )
    valid = np.isfinite(destination) & (destination > 0)
    rgba = np.zeros((size, size, 4), dtype=np.uint8)
    if valid.any():
        scale = float(np.percentile(np.log1p(destination[valid]), 99))
        normalized = np.clip(np.log1p(np.maximum(destination, 0)) / max(scale, 1e-6), 0, 1)
        rgba[..., 0] = 18
        rgba[..., 1] = 90
        rgba[..., 2] = 145
        rgba[..., 3] = np.where(valid, np.maximum(8, normalized * 245), 0).astype(np.uint8)
    output = Path(output_png)
    output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, mode="RGBA").save(output, optimize=True)
    write_json(output_metadata, {
        "kind": "raster", "file": output.name,
        "source": "External user-provided GeoTIFF; verify license and original metadata",
        "metric": "Original raster values; logarithmic display", "bounds_wgs84": [-180, -85.051129, 180, 85.051129],
        "period": period, "source_url": source_url, "coverage": "defined by source raster", "reduction": "mean reprojection to EPSG:3857"
    })
    return str(output)
