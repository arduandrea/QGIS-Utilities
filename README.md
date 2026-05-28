# QGIS Utilities

A collection of headless PyQGIS scripts for common geospatial processing tasks.
All scripts run outside the QGIS GUI, work on macOS, Windows, and Linux,
and share a common bootstrap module in `misc/`.

---

## Repository Structure

```
QGIS-Utilities/
├── misc/
│   └── qgis_env.py              # Shared QGIS path detection + Windows env setup
├── Reprojection/
│   ├── warp_reprojection.py     # Batch reproject GeoTIFFs to any CRS
│   └── README.md
└── ShapGPKG-Converter/
    ├── shp_to_gpkg_converter.py # Convert Shapefile(s) to GeoPackage
    └── README.md
```

---

## Scripts

### Reprojection — `warp_reprojection.py`

Batch-reprojects GeoTIFF tiles using QGIS `gdal:warpreproject`.

- Processes entire year-labelled folder trees
- Configurable target CRS, resampling method, compression, and resolution
- Real-time per-file progress with size reporting

```bash
python Reprojection/warp_reprojection.py \
  --input 2021:/data/tiles/2021 \
  --input 2022:/data/tiles/2022 \
  --target-crs EPSG:4326
```

→ See [`Reprojection/README.md`](Reprojection/README.md) for full usage.

---

### ShapGPKG Converter — `shp_to_gpkg_converter.py`

Converts one or more Shapefiles to GeoPackage using QGIS `native:package`.

- Single file, multi-file (multiple layers into one GPKG), and batch folder modes
- Optional merge of an entire folder into one GeoPackage
- Cleans up Shapefile sidecar files after conversion
- Real-time progress bar with feature count and size reporting

```bash
# Single file
python ShapGPKG-Converter/shp_to_gpkg_converter.py \
  --input parcels.shp --output parcels.gpkg

# Batch folder
python ShapGPKG-Converter/shp_to_gpkg_converter.py \
  --input-dir /data/shapefiles \
  --output-dir /data/geopackages
```

→ See [`ShapGPKG-Converter/README.md`](ShapGPKG-Converter/README.md) for full usage.

---

## Shared Utilities — `misc/qgis_env.py`

All scripts import `find_qgis_paths()` and `setup_windows_env()` from `misc/qgis_env.py`.

| Function | Description |
|----------|-------------|
| `find_qgis_paths()` | Auto-detects QGIS prefix, Python lib, and plugins dir by OS. Checks `QGIS_PREFIX` / `QGIS_PYTHON` env vars first. |
| `setup_windows_env()` | Sets `GDAL_DATA`, `PROJ_LIB`, `QT_PLUGIN_PATH`, and `PATH` for standalone PyQGIS on Windows. |

Override auto-detection with env vars (applies to all scripts):

```bash
export QGIS_PREFIX=/Applications/QGIS.app/Contents/MacOS
export QGIS_PYTHON=/Applications/QGIS.app/Contents/MacOS/lib/python3.12
```

---

## Requirements

- QGIS 3.x installed
- Run scripts with the **system Python**, not QGIS's internal interpreter
