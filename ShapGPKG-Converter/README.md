# shp_to_gpkg — Shapefile to GeoPackage

Converts one or more Shapefiles to GeoPackage format using QGIS's `native:package` algorithm.
Runs headless (no GUI), supports single file, multi-file, and batch folder modes.
Works on macOS, Windows, and Linux.

---

## Requirements

- QGIS 3.x installed (the script uses its bundled Python and GDAL)
- Run with the **system Python** (not QGIS's internal Python interpreter)
- `misc/qgis_env.py` must be present at the repo root level (shared bootstrap utilities)

---

## Quick Start

### Single file

```bash
# macOS / Linux
python shp_to_gpkg_converter.py --input file.shp --output output.gpkg

# Windows
python shp_to_gpkg_converter.py --input C:\GIS\file.shp --output C:\GIS\output.gpkg
```

### Multiple Shapefiles → one GeoPackage

Each `.shp` becomes a separate layer inside the same `.gpkg`.

```bash
python shp_to_gpkg_converter.py \
  --input roads.shp buildings.shp water.shp \
  --output combined.gpkg
```

### Batch folder — one `.gpkg` per `.shp`

```bash
python shp_to_gpkg_converter.py \
  --input-dir /path/to/shapefiles \
  --output-dir /path/to/geopackages
```

### Batch folder — all `.shp` merged into one `.gpkg`

```bash
python shp_to_gpkg_converter.py \
  --input-dir /path/to/shapefiles \
  --output /path/to/combined.gpkg \
  --merge
```

### No CLI flags — edit the script directly

Open `shp_to_gpkg_converter.py` and populate the static config section:

```python
INPUT      = "/path/to/file.shp"
OUTPUT     = "/path/to/output.gpkg"

# — or for batch folder mode —
INPUT_DIR  = "/path/to/shapefiles"
OUTPUT_DIR = "/path/to/geopackages"   # optional, defaults to INPUT_DIR
```

---

## Output

- Output `.gpkg` is written to the path specified by `--output` or `--output-dir`.
- If `--output-dir` is not provided in batch mode, `.gpkg` files are written next to the `.shp` files.
- By default, original Shapefile sidecar files (`.shp`, `.shx`, `.dbf`, `.prj`, `.cpg`, `.qpj`, `.sbn`, `.sbx`) are **deleted** after a successful conversion. Use `--no-cleanup` to keep them.

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
python shp_to_gpkg_converter.py --input file.shp --output file.gpkg
```

Or via **CLI flags**:

```bash
python shp_to_gpkg_converter.py \
  --qgis-prefix /Applications/QGIS.app/Contents/MacOS \
  --qgis-python /Applications/QGIS.app/Contents/MacOS/lib/python3.12 \
  --input file.shp --output file.gpkg
```

---

## All CLI Arguments

### Input

| Argument | Description |
|----------|-------------|
| `--input FILE [FILE ...]` | One or more `.shp` files. Packaged into a single `.gpkg`. Requires `--output`. |
| `--input-dir DIR` | Folder of `.shp` files. Pairs with `--output-dir` or `--output --merge`. |

`--input` and `--input-dir` are mutually exclusive.

### Output

| Argument | Default | Description |
|----------|---------|-------------|
| `--output FILE.gpkg` | — | Output GeoPackage path. Required for `--input` and `--input-dir --merge`. |
| `--output-dir DIR` | same as `--input-dir` | Output folder in batch mode. One `.gpkg` per `.shp`. |
| `--merge` | off | With `--input-dir`: package all Shapefiles into one GeoPackage. Requires `--output`. |

### Conversion Options

| Argument | Default | Description |
|----------|---------|-------------|
| `--no-overwrite` | *(overwrite on)* | Do not overwrite existing GeoPackage. |
| `--save-styles` | off | Save layer styles to GeoPackage. |
| `--save-metadata` | off | Save layer metadata to GeoPackage. |
| `--selected-only` | off | Export selected features only. |
| `--no-cleanup` | *(cleanup on)* | Keep original Shapefile sidecar files after conversion. |

### QGIS Path Overrides

| Argument | Description |
|----------|-------------|
| `--qgis-prefix` | QGIS prefix path (overrides auto-detection). |
| `--qgis-python` | QGIS Python lib path (overrides auto-detection). |

---

## Examples

```bash
# Single file, keep original shapefiles
python shp_to_gpkg_converter.py \
  --input parcels.shp \
  --output parcels.gpkg \
  --no-cleanup

# Batch folder, custom output directory
python shp_to_gpkg_converter.py \
  --input-dir /data/raw_shapefiles \
  --output-dir /data/geopackages

# Merge all shapefiles in a folder into one GPKG with styles
python shp_to_gpkg_converter.py \
  --input-dir /data/layers \
  --output /data/project.gpkg \
  --merge \
  --save-styles

# Windows — explicit QGIS path, batch mode
python shp_to_gpkg_converter.py \
  --qgis-prefix "C:\Program Files\QGIS 3.34\apps\qgis" \
  --input-dir C:\GIS\shapefiles \
  --output-dir C:\GIS\geopackages
```

---

## Progress Output

Each conversion prints a real-time progress bar and QGIS processing logs:

```
────────────────────────────────────────────────────────
  [1/3] parcels.shp
  Output : /data/parcels.gpkg
    parcels.shp  45.2 MB  128,450 features

  [██████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]  40%  2.1s
  [████████████████████████████████████████████████████] 100%  4.8s

  Done in 4.8s
  GeoPackage : 38.7 MB  →  /data/parcels.gpkg
  Cleaned up: parcels.shp, parcels.shx, parcels.dbf, parcels.prj
```
