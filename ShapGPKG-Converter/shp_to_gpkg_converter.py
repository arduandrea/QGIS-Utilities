import sys
import os
import time
import platform
import argparse
from pathlib import Path

# ── 1. QGIS path auto-detection ───────────────────────────────────────────────
#
# Override auto-detection via env vars:
#   QGIS_PREFIX  – QGIS app prefix   (e.g. /Applications/QGIS.app/Contents/MacOS)
#   QGIS_PYTHON  – QGIS Python lib   (e.g. …/MacOS/lib/python3.x)
#
# Or pass --qgis-prefix / --qgis-python on the command line.

def find_qgis_paths():
    env_prefix = os.environ.get("QGIS_PREFIX", "")
    env_python = os.environ.get("QGIS_PYTHON", "")
    if env_prefix and env_python:
        plugins = str(Path(env_prefix) / "python" / "plugins")
        return env_prefix, env_python, plugins

    system = platform.system()

    if system == "Darwin":
        candidates = sorted(Path("/Applications").glob("QGIS*.app"), reverse=True)
        if not candidates:
            return "", "", ""
        base    = candidates[0] / "Contents" / "MacOS"
        py_lib  = next(iter(sorted(base.glob("lib/python3.*"), reverse=True)), None)
        plugins = candidates[0] / "Contents" / "Resources" / "python" / "plugins"
        return str(base), str(py_lib) if py_lib else "", str(plugins)

    if system == "Windows":
        search_roots = list(filter(None, [
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramW6432"),
            r"C:\Program Files",
            r"C:\Program Files (x86)",
        ]))
        for root in search_roots:
            for qgis_root in sorted(Path(root).glob("QGIS*"), reverse=True):
                qgis_app = qgis_root / "apps" / "qgis"
                if not qgis_app.exists():
                    continue
                py_dir  = next(iter(sorted((qgis_root / "apps").glob("Python3*"), reverse=True)), None)
                plugins = qgis_app / "python" / "plugins"
                return str(qgis_app), str(py_dir) if py_dir else "", str(plugins)
        return "", "", ""

    if system == "Linux":
        for base in [Path("/usr"), Path("/usr/local")]:
            if (base / "share" / "qgis").exists():
                py_lib  = next(iter(sorted(base.glob("lib/python3.*"), reverse=True)), None)
                plugins = base / "share" / "qgis" / "python" / "plugins"
                return str(base), str(py_lib) if py_lib else "", str(plugins)
        return "", "", ""

    return "", "", ""


def setup_windows_env(prefix_path: str):
    """Set GDAL/PROJ/Qt env vars needed for standalone PyQGIS on Windows."""
    qgis_root = Path(prefix_path).parent.parent
    additions = {
        "GDAL_DATA":        str(qgis_root / "share" / "gdal"),
        "PROJ_LIB":         str(qgis_root / "share" / "proj"),
        "QT_PLUGIN_PATH":   str(qgis_root / "apps" / "Qt5" / "plugins"),
        "GDAL_DRIVER_PATH": str(qgis_root / "apps" / "gdal" / "lib" / "gdalplugins"),
    }
    for key, val in additions.items():
        if Path(val).exists():
            os.environ[key] = val
    extra_path = os.pathsep.join([
        str(qgis_root / "bin"),
        str(Path(prefix_path) / "bin"),
    ])
    os.environ["PATH"] = extra_path + os.pathsep + os.environ.get("PATH", "")


# ── 2. CLI arguments ──────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert Shapefile(s) to GeoPackage via QGIS native:package.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Input — mutually exclusive modes
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--input", nargs="+", metavar="FILE.shp",
        help="One or more Shapefiles to package into a single GeoPackage.",
    )
    input_group.add_argument(
        "--input-dir", metavar="DIR",
        help="Folder containing .shp files. Pairs with --output-dir or --output.",
    )

    # Output
    parser.add_argument(
        "--output", metavar="FILE.gpkg",
        help="Output GeoPackage path. Required when using --input or --input-dir with --merge.",
    )
    parser.add_argument(
        "--output-dir", metavar="DIR",
        help="Output folder for batch mode (--input-dir). One .gpkg per .shp.",
    )
    parser.add_argument(
        "--merge", action="store_true",
        help="With --input-dir: package all found Shapefiles into a single GeoPackage (requires --output).",
    )

    # Conversion options
    parser.add_argument("--overwrite",              action="store_true", default=True,
                        help="Overwrite existing GeoPackage.")
    parser.add_argument("--no-overwrite",           dest="overwrite", action="store_false",
                        help="Do not overwrite existing GeoPackage.")
    parser.add_argument("--save-styles",            action="store_true",
                        help="Save layer styles to GeoPackage.")
    parser.add_argument("--save-metadata",          action="store_true",
                        help="Save layer metadata to GeoPackage.")
    parser.add_argument("--selected-only",          action="store_true",
                        help="Export selected features only.")
    parser.add_argument("--no-cleanup",             action="store_true",
                        help="Keep original Shapefile sidecar files after conversion.")

    # QGIS path overrides
    parser.add_argument("--qgis-prefix", default=None,
                        help="QGIS prefix path (overrides auto-detection).")
    parser.add_argument("--qgis-python", default=None,
                        help="QGIS Python lib path (overrides auto-detection).")

    return parser.parse_args()


# ── 3. Static config (used when no CLI flags are provided) ────────────────────
#
# Fill these in to run the script without any command-line arguments.

INPUT      = None   # e.g. "/path/to/file.shp"  or  r"C:\GIS\file.shp"
OUTPUT     = None   # e.g. "/path/to/output.gpkg"
INPUT_DIR  = None   # e.g. "/path/to/shp_folder"
OUTPUT_DIR = None   # e.g. "/path/to/gpkg_folder"

# ── 4. Bootstrap ──────────────────────────────────────────────────────────────

args = parse_args()

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

print("[ 1/3 ] Loading QGIS...", flush=True)
from qgis.core import QgsApplication, QgsProcessingFeedback, QgsVectorLayer
from processing.core.Processing import Processing
import processing

app = QgsApplication([], False)
app.setPrefixPath(qgis_prefix, True)
app.initQgis()
print("[ 2/3 ] Initialising Processing framework...", flush=True)
Processing.initialize()
print("[ 3/3 ] Ready.\n", flush=True)

# ── 5. Helpers ────────────────────────────────────────────────────────────────

def format_time(seconds):
    h, rem = divmod(int(seconds), 3600)
    m, s   = divmod(rem, 60)
    if h > 0: return f"{h}h {m}m {s}s"
    if m > 0: return f"{m}m {s}s"
    return f"{seconds:.1f}s"

def file_size_mb(file_path):
    try:
        return Path(file_path).stat().st_size / (1024 * 1024)
    except OSError:
        return 0.0

def count_features(shp_path):
    try:
        lyr = QgsVectorLayer(str(shp_path), "tmp", "ogr")
        return lyr.featureCount() if lyr.isValid() else "?"
    except Exception:
        return "?"

def print_separator(char="─", width=56):
    print(char * width, flush=True)

def cleanup_shapefile(shp_path: Path):
    removed = []
    for ext in (".shp", ".shx", ".dbf", ".prj", ".cpg", ".qpj", ".sbn", ".sbx"):
        sidecar = shp_path.with_suffix(ext)
        if sidecar.exists():
            sidecar.unlink()
            removed.append(sidecar.name)
    if removed:
        print(f"  Cleaned up: {', '.join(removed)}", flush=True)


class VerboseFeedback(QgsProcessingFeedback):
    def __init__(self, step_start):
        super().__init__()
        self._last_pct  = -1
        self._start     = step_start
        self._last_info = ""

    def pushInfo(self, info):
        info = info.strip()
        if info and info != self._last_info:
            self._last_info = info
            print(f"  [info  | {format_time(time.time()-self._start)}] {info}", flush=True)

    def pushWarning(self, warning):
        warning = warning.strip()
        if warning:
            print(f"  [warn  | {format_time(time.time()-self._start)}] {warning}", flush=True)

    def reportError(self, error, fatalError=False):
        error = error.strip()
        if error:
            print(f"  [error | {format_time(time.time()-self._start)}] {error}", flush=True)

    def setProgress(self, progress):
        pct = int(progress)
        if pct != self._last_pct:
            self._last_pct = pct
            elapsed = format_time(time.time() - self._start)
            filled  = int(pct / 2)
            bar     = "█" * filled + "░" * (50 - filled)
            print(f"  [{bar}] {pct:3d}%  {elapsed}", flush=True)


# ── 6. Build job list ─────────────────────────────────────────────────────────
#
# Each job: (list[Path], Path)  →  (input shapefiles, output gpkg)

jobs: list[tuple[list[Path], Path]] = []

if args.input:
    # Explicit file list → one GPKG
    if not args.output:
        sys.exit("ERROR: --output is required when using --input.")
    input_paths = [Path(f) for f in args.input]
    jobs.append((input_paths, Path(args.output)))

elif args.input_dir:
    src_dir = Path(args.input_dir)
    shp_files = sorted(src_dir.glob("*.shp"))
    if not shp_files:
        sys.exit(f"ERROR: No .shp files found in {src_dir}")

    if args.merge:
        if not args.output:
            sys.exit("ERROR: --output is required with --input-dir --merge.")
        jobs.append((shp_files, Path(args.output)))
    else:
        out_dir = Path(args.output_dir) if args.output_dir else src_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        for shp in shp_files:
            jobs.append(([shp], out_dir / f"{shp.stem}.gpkg"))

else:
    # Fall back to static config at top of script
    static_input     = INPUT      or ""
    static_output    = OUTPUT     or ""
    static_input_dir = INPUT_DIR  or ""
    static_out_dir   = OUTPUT_DIR or ""
    if static_input and static_output:
        jobs.append(([Path(static_input)], Path(static_output)))
    elif static_input_dir:
        src_dir   = Path(static_input_dir)
        shp_files = sorted(src_dir.glob("*.shp"))
        out_dir   = Path(static_out_dir) if static_out_dir else src_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        for shp in shp_files:
            jobs.append(([shp], out_dir / f"{shp.stem}.gpkg"))
    else:
        sys.exit(
            "ERROR: No input specified.\n"
            "  Use --input / --input-dir, or set INPUT / INPUT_DIR in the script."
        )

# ── 7. Run conversions ────────────────────────────────────────────────────────

total_ok    = 0
total_err   = 0
batch_start = time.time()

print_separator("═")
print("  Shapefile → GeoPackage")
print_separator("═")
print(f"  Jobs      : {len(jobs)}")
print(f"  Platform  : {platform.system()}")
print(f"  Overwrite : {args.overwrite}")
print(f"  Cleanup   : {not args.no_cleanup}")
print_separator("═")
print(flush=True)

for job_idx, (input_files, output_gpkg) in enumerate(jobs, 1):
    job_label = f"[{job_idx}/{len(jobs)}]"

    # Validate inputs
    missing = [f for f in input_files if not f.exists()]
    if missing:
        for missing_file in missing:
            print(f"  {job_label} SKIP — file not found: {missing_file}", flush=True)
        total_err += 1
        continue

    print_separator()
    print(f"  {job_label} {', '.join(f.name for f in input_files)}", flush=True)
    print(f"  Output : {output_gpkg}", flush=True)
    for shp in input_files:
        feat = count_features(shp)
        feat_str = f"{feat:,}" if isinstance(feat, int) else feat
        print(f"    {shp.name}  {file_size_mb(shp):.1f} MB  {feat_str} features", flush=True)
    print(flush=True)

    output_gpkg.parent.mkdir(parents=True, exist_ok=True)

    start    = time.time()
    feedback = VerboseFeedback(start)

    try:
        processing.run(
            "native:package",
            {
                "LAYERS":                 [str(f) for f in input_files],
                "OUTPUT":                 str(output_gpkg),
                "OVERWRITE":              args.overwrite,
                "SAVE_STYLES":            args.save_styles,
                "SAVE_METADATA":          args.save_metadata,
                "SELECTED_FEATURES_ONLY": args.selected_only,
            },
            feedback=feedback,
        )
        elapsed = time.time() - start
        print(flush=True)
        print(f"  Done in {format_time(elapsed)}", flush=True)
        print(f"  GeoPackage : {file_size_mb(output_gpkg):.1f} MB  →  {output_gpkg}", flush=True)

        if not args.no_cleanup:
            for shp in input_files:
                cleanup_shapefile(shp)

        total_ok += 1

    except Exception as exc:
        elapsed = time.time() - start
        print(f"\n  FAILED after {format_time(elapsed)}: {exc}", flush=True)
        total_err += 1

    print(flush=True)

# ── 8. Summary ────────────────────────────────────────────────────────────────

total_elapsed = time.time() - batch_start
print_separator("═")
print(f"  Batch complete in {format_time(total_elapsed)}")
print(f"  Succeeded : {total_ok}")
if total_err:
    print(f"  Failed    : {total_err}")
print_separator("═")
print(flush=True)

# ── 9. Cleanup ────────────────────────────────────────────────────────────────

app.exitQgis()
