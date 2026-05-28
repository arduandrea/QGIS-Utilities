"""
Shared QGIS bootstrap utilities.

Provides:
  find_qgis_paths()      – auto-detect QGIS prefix, Python lib, and plugins dir
  setup_windows_env()    – set GDAL/PROJ/Qt env vars for standalone PyQGIS on Windows

Override auto-detection via env vars:
  QGIS_PREFIX  – e.g. /Applications/QGIS.app/Contents/MacOS
  QGIS_PYTHON  – e.g. …/MacOS/lib/python3.x
"""

import os
import platform
from pathlib import Path


def find_qgis_paths() -> tuple[str, str, str]:
    """
    Return (qgis_prefix, qgis_python, qgis_plugins).
    Checks QGIS_PREFIX / QGIS_PYTHON env vars first, then auto-detects by OS.
    Returns ('', '', '') if QGIS is not found.
    """
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


def setup_windows_env(prefix_path: str) -> None:
    """
    Set GDAL_DATA, PROJ_LIB, QT_PLUGIN_PATH, GDAL_DRIVER_PATH, and PATH
    so that standalone PyQGIS works outside the OSGeo4W shell on Windows.
    Only sets variables whose target paths exist on disk.
    """
    qgis_root = Path(prefix_path).parent.parent  # …/QGIS 3.x
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
