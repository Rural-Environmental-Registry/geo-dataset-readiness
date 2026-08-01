"""
build_plugin.py - Packages the QGIS plugin into a ZIP for installation

Generates the file in the format: geo_dataset_readiness_YYYYMMDD_HHMM.zip

Usage:
    python build_plugin.py
"""

import os
import zipfile
from datetime import datetime
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent

# Plugin directory
PLUGIN_DIR = PROJECT_ROOT / "geo-dataset-readiness"

# Plugin name inside the ZIP
PLUGIN_ZIP_NAME = "geo-dataset-readiness"

# Output directory
OUTPUT_DIR = PROJECT_ROOT / "output"

# Extensions to include in the ZIP
INCLUDE_EXTENSIONS = (".py", ".txt", ".png", ".svg", ".ui", ".ico", ".json", ".jpg", ".jpeg")


def build_zip():
    """Generates the plugin ZIP with a timestamp in the name."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    zip_name = f"geo_dataset_readiness_{timestamp}.zip"
    zip_path = OUTPUT_DIR / zip_name

    # Collect plugin files (recursively to include assets/)
    files = []
    for f in PLUGIN_DIR.rglob("*"):
        if f.is_file() and f.suffix in INCLUDE_EXTENSIONS:
            # Skip __pycache__ and output
            relative = f.relative_to(PLUGIN_DIR)
            if "__pycache__" in str(relative) or str(relative).startswith("output"):
                continue
            files.append(f)

    if not files:
        print("No files found to package.")
        return

    # Create ZIP
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(files):
            relative = file.relative_to(PLUGIN_DIR)
            arcname = f"{PLUGIN_ZIP_NAME}/{relative}"
            zf.write(file, arcname)
            print(f"  + {arcname}")

    print(f"\nZIP generated: {zip_path}")
    print(f"Files: {len(files)}")
    print(f"Size: {zip_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    build_zip()
