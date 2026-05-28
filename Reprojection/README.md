# Warp Reprojection — Batch GeoTIFF Reprojection

Batch-reprojects GeoTIFF tiles using QGIS's `gdal:warpreproject` algorithm.
Runs headless (no GUI), works on macOS, Windows, and Linux.

---

## Requirements

- QGIS 3.x installed (the script uses its bundled Python and GDAL)
- Run with the **system Python** (not QGIS's internal Python interpreter)

---

## Quick Start

### Option A — pass folders on the command line

```bash
# macOS / Linux
python warp_reprojection.py --input 2021:/path/to/tiles/2021

# Windows
python warp_reprojection.py --input 2021:C:\GIS\tiles\2021
```

### Option B — edit the script directly

Open `esri_warp_v1.py` and populate `YEAR_FOLDERS`:

```python
YEAR_FOLDERS = {
    "2021": "/Volumes/GIS/ESRI_LandCover/2021",   # macOS
    # "2021": r"C:\GIS\ESRI_LandCover\2021",       # Windows
}
```

Then run without any `--input` flag:

```bash
python warp_reprojection.py
```

---

## Output

For each input folder a `reprojected/` subfolder is created automatically.
Output files are named `<original_stem>_reprojected.tif`.

```
2021/
├── tile_001.tif
├── tile_002.tif
└── reprojected/
    ├── tile_001_reprojected.tif
    └── tile_002_reprojected.tif
```

---

## QGIS Path Detection

The script auto-detects QGIS on all platforms:

| Platform | Search location |
|----------|----------------|
| macOS    | `/Applications/QGIS*.app` (picks newest) |
| Windows  | `%ProgramFiles%\QGIS*` (picks newest) |
| Linux    | `/usr/share/qgis`, `/usr/local/share/qgis` |

If auto-detection fails, override via **env vars**:

```bash
export QGIS_PREFIX=/Applications/QGIS.app/Contents/MacOS
export QGIS_PYTHON=/Applications/QGIS.app/Contents/MacOS/lib/python3.12
python warp_reprojection.py --input 2021:/data/2021
```

Or via **CLI flags**:

```bash
python warp_reprojection.py \
  --qgis-prefix /Applications/QGIS.app/Contents/MacOS \
  --qgis-python /Applications/QGIS.app/Contents/MacOS/lib/python3.12 \
  --input 2021:/data/2021
```

---

## All CLI Arguments

### Input / Output

| Argument | Default | Description |
|----------|---------|-------------|
| `--input YEAR:PATH` | — | Input folder mapped to a year label. Repeatable for multiple years. |
| `--output-subfolder` | `reprojected` | Subfolder name created inside each input folder. |
| `--extensions` | `.tif .tiff` | File extensions to process (space-separated). |

### CRS & Resampling

| Argument | Default | Description |
|----------|---------|-------------|
| `--target-crs` | `EPSG:4326` | Target CRS — any string QGIS accepts (e.g. `EPSG:3857`). |
| `--source-crs` | *(from file)* | Override source CRS. Leave unset to read from each file. |
| `--resampling` | `0` | Resampling method index. See table below. |
| `--nodata` | `0` | NoData value written to output. |
| `--target-resolution` | *(from file)* | Output pixel size in target CRS units. |
| `--data-type` | `0` | Output data type index (`0` = same as input). |

**Resampling method indices**

| Index | Method |
|-------|--------|
| 0 | Nearest Neighbour |
| 1 | Bilinear |
| 2 | Cubic |
| 3 | Cubic Spline |
| 4 | Lanczos |
| 5 | Average |
| 6 | Mode |

### Compression & Performance

| Argument | Default | Description |
|----------|---------|-------------|
| `--creation-options` | `COMPRESS=DEFLATE\|PREDICTOR=2\|ZLEVEL=1` | GDAL creation options, pipe-separated. |
| `--no-multithreading` | *(off)* | Disable GDAL multithreading. |
| `--extra` | *(empty)* | Extra arguments passed directly to `gdalwarp`. |

### QGIS Path Overrides

| Argument | Description |
|----------|-------------|
| `--qgis-prefix` | QGIS prefix path (overrides auto-detection). |
| `--qgis-python` | QGIS Python lib path (overrides auto-detection). |

---

## Examples

```bash
# Two years, custom target CRS
python warp_reprojection.py \
  --input 2021:/data/2021 \
  --input 2022:/data/2022 \
  --target-crs EPSG:3857

# Bilinear resampling, no compression
python warp_reprojection.py \
  --input 2021:/data/2021 \
  --resampling 1 \
  --creation-options ""

# Custom output subfolder
python warp_reprojection.py \
  --input 2021:/data/2021 \
  --output-subfolder wgs84

# Windows — explicit QGIS path
python warp_reprojection.py \
  --qgis-prefix "C:\Program Files\QGIS 3.34\apps\qgis" \
  --input 2021:C:\GIS\2021
```
