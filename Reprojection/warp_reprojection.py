import sys
import time
import platform
import argparse
from pathlib import Path

# ── 1. Shared QGIS bootstrap utilities ───────────────────────────────────────
#
# find_qgis_paths / setup_windows_env live in misc/qgis_env.py.
# Override auto-detection via env vars:
#   QGIS_PREFIX  – path to QGIS app prefix  (e.g. /Applications/QGIS.app/Contents/MacOS)
#   QGIS_PYTHON  – path to QGIS Python lib  (e.g. …/MacOS/lib/python3.x)
#
# Or pass --qgis-prefix / --qgis-python on the command line.

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "misc"))
from qgis_env import find_qgis_paths, setup_windows_env

# ── 2. CLI arguments ──────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Batch-reproject GeoTIFF tiles via QGIS gdal:warpreproject.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Input/output
    parser.add_argument(
        "--input", metavar="YEAR:PATH", action="append", dest="inputs",
        help="Year→folder mapping (repeatable). Example: --input 2021:/data/2021 --input 2022:/data/2022. "
             "If omitted, edit YEAR_FOLDERS at the top of the script.",
    )
    parser.add_argument("--output-subfolder", default="reprojected",
                        help="Subfolder created inside each input folder for reprojected files.")
    parser.add_argument("--extensions", nargs="+", default=[".tif", ".tiff"],
                        help="File extensions to process.")

    # CRS / resampling
    parser.add_argument("--target-crs",     default="EPSG:4326", help="Target CRS (any QGIS-accepted string).")
    parser.add_argument("--source-crs",     default=None,        help="Source CRS override (default: read from file).")
    parser.add_argument("--resampling",     type=int, default=0, help="Resampling method index (0=Nearest Neighbour).")
    parser.add_argument("--nodata",         type=float, default=0, help="NoData value for output.")
    parser.add_argument("--target-resolution", type=float, default=None, help="Output resolution in target CRS units.")
    parser.add_argument("--data-type",      type=int, default=0, help="Output data type index (0=same as input).")

    # Compression / performance
    parser.add_argument("--creation-options", default="COMPRESS=DEFLATE|PREDICTOR=2|ZLEVEL=1",
                        help="GDAL creation options, pipe-separated.")
    parser.add_argument("--no-multithreading", action="store_true",
                        help="Disable GDAL multithreading.")
    parser.add_argument("--extra", default="", help="Extra GDAL warp arguments.")

    # QGIS paths (override auto-detection)
    parser.add_argument("--qgis-prefix", default=None, help="QGIS prefix path (overrides auto-detection).")
    parser.add_argument("--qgis-python", default=None, help="QGIS Python lib path (overrides auto-detection).")

    return parser.parse_args()


# ── 3. Static year→folder map (fallback when --input not used) ────────────────

YEAR_FOLDERS = {
    # "2021": r"C:\GIS\ESRI_LandCover\2021",   # Windows example
    # "2021": "/Volumes/GIS/ESRI_LandCover/2021",  # macOS example
}

# ── 4. Bootstrap ──────────────────────────────────────────────────────────────

args = parse_args()

# Resolve QGIS paths
qgis_prefix, qgis_python, qgis_plugins = find_qgis_paths()
if args.qgis_prefix:
    qgis_prefix = args.qgis_prefix
if args.qgis_python:
    qgis_python = args.qgis_python

if not qgis_prefix:
    sys.exit(
        "ERROR: QGIS installation not found.\n"
        "  Set QGIS_PREFIX / QGIS_PYTHON env vars, or pass --qgis-prefix / --qgis-python."
    )

if platform.system() == "Windows":
    setup_windows_env(qgis_prefix)

for sys_path_entry in filter(None, [
    qgis_python,
    str(Path(qgis_python) / "site-packages") if qgis_python else "",
    str(Path(qgis_python) / "Lib" / "site-packages") if qgis_python else "",
    str(Path(qgis_prefix) / "python"),
    qgis_plugins,
]):
    if sys_path_entry not in sys.path:
        sys.path.insert(0, sys_path_entry)

print("[ 1/3 ] Loading QGIS application...", flush=True)
from qgis.core import QgsApplication, QgsCoordinateReferenceSystem
from processing.core.Processing import Processing
import processing

app = QgsApplication([], False)
app.setPrefixPath(qgis_prefix, True)
app.initQgis()
print("[ 2/3 ] Initialising Processing framework...", flush=True)
Processing.initialize()
print("[ 3/3 ] Ready.\n", flush=True)

# ── 5. Build year→folder map from args or static config ──────────────────────

if args.inputs:
    year_folders = {}
    for entry in args.inputs:
        if ":" not in entry:
            sys.exit(f"ERROR: --input must be YEAR:PATH, got: {entry!r}")
        year, _, path = entry.partition(":")
        year_folders[year.strip()] = path.strip()
else:
    year_folders = YEAR_FOLDERS

if not year_folders:
    sys.exit(
        "ERROR: No input folders specified.\n"
        "  Use --input YEAR:PATH or edit YEAR_FOLDERS in the script."
    )

TARGET_CRS        = QgsCoordinateReferenceSystem(args.target_crs)
EXTENSIONS        = tuple(e if e.startswith(".") else f".{e}" for e in args.extensions)
OUTPUT_SUBFOLDER  = args.output_subfolder
MULTITHREADING    = not args.no_multithreading

# ── 6. Helpers ────────────────────────────────────────────────────────────────

def file_size_mb(file_path):
    try:
        return Path(file_path).stat().st_size / (1024 * 1024)
    except OSError:
        return 0.0

def format_time(seconds):
    if seconds < 60:
        return f"{seconds:.1f}s"
    return f"{int(seconds // 60)}m {int(seconds % 60)}s"

def print_separator(char="─", width=56):
    print(char * width, flush=True)

# ── 7. Collect files ──────────────────────────────────────────────────────────

all_files = []
for year, folder in year_folders.items():
    folder_path = Path(folder)
    if folder_path.is_dir():
        for f in folder_path.iterdir():
            if f.suffix.lower() in EXTENSIONS:
                all_files.append((year, folder_path, f.name))
    else:
        print(f"  WARNING: folder not found, skipping — {folder}", flush=True)

total_files = len(all_files)

# ── 8. Batch processing ───────────────────────────────────────────────────────

total_ok    = 0
total_err   = 0
batch_start = time.time()

print_separator("═")
print(f"  ESRI 10m Land Cover — Batch Reproject")
print_separator("═")
print(f"  Files found : {total_files}")
print(f"  Years       : {', '.join(year_folders.keys())}")
print(f"  Target CRS  : {args.target_crs}")
print(f"  Resampling  : {args.resampling}")
print(f"  Compression : {args.creation_options}")
print(f"  Platform    : {platform.system()}")
print_separator("═")
print(flush=True)

current_year = None
file_counter = 0

for year, input_folder, filename in all_files:
    file_counter += 1

    if year != current_year:
        current_year   = year
        output_folder  = input_folder / OUTPUT_SUBFOLDER
        output_folder.mkdir(parents=True, exist_ok=True)
        year_files = sum(1 for y, _, _ in all_files if y == year)
        print(flush=True)
        print_separator()
        print(f"  {year}  —  {year_files} file(s)  →  {output_folder}")
        print_separator()

    input_path  = input_folder / filename
    output_folder = input_folder / OUTPUT_SUBFOLDER
    stem, ext   = Path(filename).stem, Path(filename).suffix
    output_path = output_folder / f"{stem}_reprojected{ext}"
    size_in     = file_size_mb(input_path)
    progress    = f"[{file_counter}/{total_files}]"

    print(f"\n  {progress} {filename}", flush=True)
    print(f"           Size   : {size_in:.1f} MB", flush=True)
    print(f"           Input  : {input_path}", flush=True)
    print(f"           Output : {output_path}", flush=True)
    print(f"           Status : processing...", flush=True)

    params = {
        "INPUT":             str(input_path),
        "SOURCE_CRS":        args.source_crs,
        "TARGET_CRS":        TARGET_CRS,
        "RESAMPLING":        args.resampling,
        "NODATA":            args.nodata,
        "TARGET_RESOLUTION": args.target_resolution,
        "DATA_TYPE":         args.data_type,
        "CREATION_OPTIONS":  args.creation_options,
        "TARGET_EXTENT":     None,
        "TARGET_EXTENT_CRS": None,
        "MULTITHREADING":    MULTITHREADING,
        "EXTRA":             args.extra,
        "OUTPUT":            str(output_path),
    }

    file_start = time.time()
    try:
        processing.run("gdal:warpreproject", params)
        elapsed  = time.time() - file_start
        size_out = file_size_mb(output_path)
        print(f"           Status : done in {format_time(elapsed)}", flush=True)
        print(f"           Out MB : {size_out:.1f}  (was {size_in:.1f})", flush=True)
        total_ok += 1
    except Exception as e:
        elapsed = time.time() - file_start
        print(f"           Status : FAILED after {format_time(elapsed)}", flush=True)
        print(f"           Error  : {e}", flush=True)
        total_err += 1

# ── 9. Summary ────────────────────────────────────────────────────────────────

total_elapsed = time.time() - batch_start
print(flush=True)
print_separator("═")
print(f"  Batch complete in {format_time(total_elapsed)}")
print(f"  Succeeded : {total_ok}")
if total_err:
    print(f"  Failed    : {total_err}")
print_separator("═")
print(flush=True)

# ── 10. Cleanup ───────────────────────────────────────────────────────────────

app.exitQgis()
