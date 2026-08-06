# -*- coding: utf-8 -*-
# Copyright (C) 2026 Dataprev
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
validator.py - Logical consistency validation engine (ISO 19157:2013)

Performs logical consistency checks on geographic datasets:
- Format consistency (dataset type: GPKG or GDB)
- Conceptual consistency (table and attribute names)
- Domain consistency (class values and intervals)
- Topological consistency (record geometries)

Can be used standalone (without QGIS) for testing.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import geopandas as gpd


class Status(Enum):
    CONFORMANT = "CONFORMANT"
    NON_CONFORMANT = "NON-CONFORMANT"
    WARNING = "WARNING"


@dataclass
class CheckResult:
    """Result of an individual check."""
    name: str
    status: Status
    details: str = ""
    category: str = ""  # format, conceptual, domain, topological
    layer: str = ""     # associated layer name (when applicable)
    wkt: str = ""       # WKT of geometry with error (detailed validation)


@dataclass
class ValidationReport:
    """Complete validation report according to ISO 19157."""
    file_path: str
    checks: list[CheckResult] = field(default_factory=list)
    log: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.status != Status.NON_CONFORMANT for c in self.checks)

    @property
    def has_warnings(self) -> bool:
        return any(c.status == Status.WARNING for c in self.checks)

    @property
    def format_checks(self) -> list[CheckResult]:
        return [c for c in self.checks if c.category == "format"]

    @property
    def conceptual_checks(self) -> list[CheckResult]:
        return [c for c in self.checks if c.category == "conceptual"]

    @property
    def domain_checks(self) -> list[CheckResult]:
        return [c for c in self.checks if c.category == "domain"]

    @property
    def topological_checks(self) -> list[CheckResult]:
        return [c for c in self.checks if c.category == "topological"]

    def summary(self) -> str:
        # Exclude per-FID detail entries from the rule count
        rule_checks = [
            c for c in self.checks
            if not (c.name.startswith("Error in feature FID") or
                    c.name.startswith("Warning in feature FID"))
        ]
        total    = len(rule_checks)
        ok       = sum(1 for c in rule_checks if c.status == Status.CONFORMANT)
        non_conf = sum(1 for c in rule_checks if c.status == Status.NON_CONFORMANT)
        warnings = sum(1 for c in rule_checks if c.status == Status.WARNING)
        parts = [f"{total} rules executed ({ok} conformant"]
        if non_conf:
            parts.append(f", {non_conf} non-conformant")
        if warnings:
            parts.append(f", {warnings} warning(s)")
        parts.append(")")
        return "".join(parts)

    def summary_by_category(self) -> dict[str, dict]:
        # FID-level detail entries (added in detailed topological mode) must not
        # be counted as individual rules — they are sub-items of "Topological errors".
        # We identify them by their name pattern: "Error in feature FID …" or
        # "Warning in feature FID …".
        def _is_fid_detail(check) -> bool:
            n = check.name
            return n.startswith("Error in feature FID") or \
                   n.startswith("Warning in feature FID")

        categories = {}
        for cat_name, checks in [
            ("Format Consistency",      self.format_checks),
            ("Conceptual Consistency",  self.conceptual_checks),
            ("Domain Consistency",      self.domain_checks),
            ("Topological Consistency", self.topological_checks),
        ]:
            if checks:
                # Exclude per-FID detail rows from the rule count
                rule_checks = [c for c in checks if not _is_fid_detail(c)]
                if not rule_checks:
                    continue
                ok       = sum(1 for c in rule_checks if c.status == Status.CONFORMANT)
                non_conf = sum(1 for c in rule_checks if c.status == Status.NON_CONFORMANT)
                warnings = sum(1 for c in rule_checks if c.status == Status.WARNING)
                if non_conf > 0:
                    status = Status.NON_CONFORMANT
                elif warnings > 0:
                    status = Status.WARNING
                else:
                    status = Status.CONFORMANT
                categories[cat_name] = {
                    "total": len(rule_checks),
                    "conformant": ok,
                    "non_conformant": non_conf,
                    "warnings": warnings,
                    "status": status,
                }
        return categories


# ---------------------------------------------------------------------------
# Validation rules configuration (loaded from geodb-layout.json)
# ---------------------------------------------------------------------------

import json as _json
import os as _os


def _load_layout() -> dict:
    """Loads the reference layout from geodb-layout.json."""
    layout_path = _os.path.join(_os.path.dirname(__file__), "geodb-layout.json")
    with open(layout_path, "r", encoding="utf-8") as f:
        return _json.load(f)


def _extract_config(layout: dict) -> tuple:
    """Extracts configuration constants from the JSON layout."""
    expected_layers = [c["name"] for c in layout["layers"]]

    layers_with_required_fields = {}
    layers_with_forbidden_fields = {}
    class_domain = {}
    absence_status = {}

    for layer in layout["layers"]:
        name = layer["name"]

        # Required fields
        if layer.get("fields"):
            layers_with_required_fields[name] = layer["fields"]

        # Forbidden fields
        if layer.get("forbidden_fields"):
            layers_with_forbidden_fields[name] = layer["forbidden_fields"]

        # Class domains
        for field_def in layer.get("fields", []):
            if field_def["name"].upper() == "CLASSE" and "domain" in field_def:
                class_domain[name] = (field_def["domain"]["min"], field_def["domain"]["max"])

        # Absence status (NON_CONFORMANT, CONFORMANT or WARNING)
        if layer.get("absence_status"):
            absence_status[name] = layer["absence_status"]

    crs_epsg = layout["crs"]["epsg"]
    crs_name = layout["crs"]["name"]
    # Build a dict of accepted (non-preferred) CRS: {epsg: name}
    accepted_crs = {
        entry["epsg"]: entry["name"]
        for entry in layout["crs"].get("accepted", [])
    }

    return expected_layers, layers_with_required_fields, layers_with_forbidden_fields, class_domain, crs_epsg, crs_name, absence_status, accepted_crs


# Load layout
_LAYOUT = _load_layout()
(
    EXPECTED_LAYERS,
    LAYERS_WITH_REQUIRED_FIELDS,
    LAYERS_WITH_FORBIDDEN_FIELDS,
    CLASS_DOMAIN,
    EXPECTED_CRS_EPSG,
    EXPECTED_CRS_NAME,
    ABSENCE_STATUS,
    ACCEPTED_CRS,          # {epsg: name} — accepted but non-preferred CRS (WARNING)
) = _extract_config(_LAYOUT)

# Derive compatibility lists
LAYERS_WITH_CLASS = [
    name for name, fields in LAYERS_WITH_REQUIRED_FIELDS.items()
    if any(f["name"].upper() == "CLASSE" for f in fields)
]
LAYERS_WITHOUT_CLASS = [
    name for name, forbidden in LAYERS_WITH_FORBIDDEN_FIELDS.items()
    if "CLASSE" in [f.upper() for f in forbidden]
]

# Accepted formats
ACCEPTED_FORMATS = {
    ".gpkg": "GeoPackage",
    ".gdb": "ESRI GeoDatabase",
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def list_layers(base_path: Path) -> list[str]:
    """Lists the layer names available in the geographic dataset."""
    import pyogrio
    layers = pyogrio.list_layers(str(base_path))
    return [layer[0] for layer in layers]


def find_layer_name(existing_layers: list[str], expected_name: str) -> Optional[str]:
    """
    Searches for the real layer name in the existing list, case-insensitive.
    Returns the real name or None if not found.
    """
    for layer in existing_layers:
        if layer.upper() == expected_name.upper():
            return layer
    return None


def detect_format(base_path: Path) -> tuple[bool, str]:
    """
    Detects and validates the dataset format.
    Returns (valid, description).
    """
    path = Path(base_path)

    if path.suffix.lower() == ".gpkg" and path.is_file():
        return True, "GeoPackage (.gpkg)"
    elif path.suffix.lower() == ".gdb" and path.is_dir():
        return True, "ESRI GeoDatabase (.gdb)"
    elif path.suffix.lower() == ".zip" and path.is_file():
        return True, "Compressed GeoPackage (.gpkg.zip)"
    elif path.suffix.lower() in ACCEPTED_FORMATS:
        return True, ACCEPTED_FORMATS[path.suffix.lower()]
    else:
        return False, f"Unrecognized format: {path.suffix}"


def extract_gpkg_from_zip(zip_path: Path) -> Optional[Path]:
    """
    Extracts the first .gpkg file from inside a ZIP to a temporary directory.
    Returns the path of the extracted .gpkg or None if not found.
    """
    import zipfile
    import tempfile

    if not zipfile.is_zipfile(zip_path):
        return None

    with zipfile.ZipFile(zip_path, "r") as zf:
        gpkg_files = [f for f in zf.namelist() if f.lower().endswith(".gpkg")]
        if not gpkg_files:
            return None

        gpkg_name = gpkg_files[0]
        temp_dir = Path(tempfile.mkdtemp(prefix="validator_"))
        zf.extract(gpkg_name, temp_dir)
        return temp_dir / gpkg_name


# ---------------------------------------------------------------------------
# FORMAT CONSISTENCY
# ---------------------------------------------------------------------------


def validate_format(base_path: Path) -> list[CheckResult]:
    """Checks whether the file is an accepted format and can be read."""
    results = []

    valid, description = detect_format(base_path)
    if valid:
        results.append(CheckResult(
            name="Dataset format",
            status=Status.CONFORMANT,
            details=f"Valid format: {description}",
            category="format",
        ))
    else:
        results.append(CheckResult(
            name="Dataset format",
            status=Status.NON_CONFORMANT,
            details=f"{description}. Accepted formats: GeoPackage (.gpkg), ESRI GeoDatabase (.gdb)",
            category="format",
        ))
        return results

    try:
        existing_layers = list_layers(base_path)
        if len(existing_layers) == 0:
            results.append(CheckResult(
                name="Dataset readability",
                status=Status.NON_CONFORMANT,
                details="Dataset readable but contains no layers",
                category="format",
            ))
        else:
            results.append(CheckResult(
                name="Dataset readability",
                status=Status.CONFORMANT,
                details=f"Dataset readable, {len(existing_layers)} layer(s) found",
                category="format",
            ))
    except Exception as e:
        err_msg = str(e)
        # Replace raw GDAL/pyogrio technical messages with user-friendly text
        _NO_FORMAT_PHRASES = (
            "not recognized as being in a supported file format",
            "not recognized as a supported file format",
            "no layers",
            "Unable to open",
            "No such file",
        )
        if any(p.lower() in err_msg.lower() for p in _NO_FORMAT_PHRASES):
            user_msg = "Dataset readable but contains no layers or is not a valid GeoPackage/GDB"
        else:
            user_msg = f"Error reading dataset: {err_msg}"
        results.append(CheckResult(
            name="Dataset readability",
            status=Status.NON_CONFORMANT,
            details=user_msg,
            category="format",
        ))

    return results


# ---------------------------------------------------------------------------
# CONCEPTUAL CONSISTENCY
# ---------------------------------------------------------------------------


def validate_conceptual_consistency(base_path: Path, layer_filter: str | None = None) -> list[CheckResult]:
    """Checks table (layer) names and presence of expected attributes."""
    results = []

    layers_to_validate = EXPECTED_LAYERS
    if layer_filter:
        layers_to_validate = [layer_filter]

    try:
        existing_layers = list_layers(base_path)
    except Exception:
        results.append(CheckResult(
            name="Layer listing",
            status=Status.NON_CONFORMANT,
            details="Could not list dataset layers",
            category="conceptual",
        ))
        return results

    missing_layers = [l for l in layers_to_validate if find_layer_name(existing_layers, l) is None]

    if not missing_layers:
        results.append(CheckResult(
            name="Layer names",
            status=Status.CONFORMANT,
            details=f"All layers found: {', '.join(layers_to_validate)}",
            category="conceptual",
            layer="(all)" if not layer_filter else layer_filter,
        ))
    else:
        for missing_layer in missing_layers:
            status_cfg = ABSENCE_STATUS.get(missing_layer, "NON_CONFORMANT")
            if status_cfg == "CONFORMANT":
                absence_status = Status.CONFORMANT
            elif status_cfg == "WARNING":
                absence_status = Status.WARNING
            else:
                absence_status = Status.NON_CONFORMANT

            results.append(CheckResult(
                name="Missing layer",
                status=absence_status,
                details=f"Layer '{missing_layer}' not found in dataset",
                category="conceptual",
                layer=missing_layer,
            ))

    for layer_name in layers_to_validate:
        real_name = find_layer_name(existing_layers, layer_name)
        if real_name is None:
            continue

        import pyogrio
        info = pyogrio.read_info(str(base_path), layer=real_name)
        row_count = info.get("features", 0) if info else 0

        if row_count == 0:
            results.append(CheckResult(
                name="Records",
                status=Status.NON_CONFORMANT,
                details=f"Layer '{real_name}' exists but has no records (empty)",
                category="conceptual",
                layer=layer_name,
            ))
        else:
            results.append(CheckResult(
                name="Records",
                status=Status.CONFORMANT,
                details=f"{row_count} record(s)",
                category="conceptual",
                layer=layer_name,
            ))

        gdf_sample = gpd.read_file(base_path, layer=real_name, rows=1)
        columns = gdf_sample.columns.tolist()

        # Guard: gpd.read_file may return a plain DataFrame (no .crs) when the
        # layer has no geometry column.  Report as a specific error and skip
        # all further checks for this layer.
        import geopandas as _gpd
        if not isinstance(gdf_sample, _gpd.GeoDataFrame):
            results.append(CheckResult(
                name="Geometry column missing",
                status=Status.NON_CONFORMANT,
                details=f"Layer '{real_name}' has no geometry column",
                category="conceptual",
                layer=layer_name,
            ))
            continue  # skip CRS / attribute checks for this layer

        if layer_name in LAYERS_WITH_CLASS:
            col_class = next((c for c in columns if c.upper() == "CLASSE"), None)
            if col_class is None:
                results.append(CheckResult(
                    name="CLASSE attribute",
                    status=Status.NON_CONFORMANT,
                    details=f"Layer '{layer_name}' is missing the required CLASSE attribute. "
                             f"Columns found: {', '.join(columns)}",
                    category="conceptual",
                    layer=layer_name,
                ))
            else:
                results.append(CheckResult(
                    name="CLASSE attribute",
                    status=Status.CONFORMANT,
                    details=f"Attribute '{col_class}' found",
                    category="conceptual",
                    layer=layer_name,
                ))

        elif layer_name in LAYERS_WITHOUT_CLASS:
            has_class = any(col.upper() == "CLASSE" for col in columns)
            if has_class:
                results.append(CheckResult(
                    name="Absence of CLASSE",
                    status=Status.NON_CONFORMANT,
                    details=f"CLASSE attribute present in '{real_name}' (should not exist)",
                    category="conceptual",
                    layer=layer_name,
                ))
            else:
                results.append(CheckResult(
                    name="Absence of CLASSE",
                    status=Status.CONFORMANT,
                    details="No CLASSE attribute (correct)",
                    category="conceptual",
                    layer=layer_name,
                ))

        if gdf_sample.crs is None:
            results.append(CheckResult(
                name="CRS",
                status=Status.NON_CONFORMANT,
                details="CRS not defined",
                category="conceptual",
                layer=layer_name,
            ))
        elif gdf_sample.crs.to_epsg() == EXPECTED_CRS_EPSG:
            results.append(CheckResult(
                name="CRS",
                status=Status.CONFORMANT,
                details=EXPECTED_CRS_NAME,
                category="conceptual",
                layer=layer_name,
            ))
        elif gdf_sample.crs.to_epsg() in ACCEPTED_CRS:
            # CRS is recognised but not the preferred standard → WARNING
            accepted_name = ACCEPTED_CRS[gdf_sample.crs.to_epsg()]
            results.append(CheckResult(
                name="CRS",
                status=Status.WARNING,
                details=(
                    f"Layer '{real_name}' uses EPSG:{gdf_sample.crs.to_epsg()} ({accepted_name}). "
                    f"Accepted, but the expected CRS is EPSG:{EXPECTED_CRS_EPSG} ({EXPECTED_CRS_NAME})"
                ),
                category="conceptual",
                layer=layer_name,
            ))
        else:
            results.append(CheckResult(
                name="CRS",
                status=Status.NON_CONFORMANT,
                details=f"Layer '{real_name}' has EPSG:{gdf_sample.crs.to_epsg()} (expected EPSG:{EXPECTED_CRS_EPSG})",
                category="conceptual",
                layer=layer_name,
            ))

    return results


# ---------------------------------------------------------------------------
# DOMAIN CONSISTENCY
# ---------------------------------------------------------------------------


def validate_domain_consistency(base_path: Path, layer_filter: str | None = None) -> list[CheckResult]:
    """Checks values and intervals of the CLASSE attribute."""
    results = []

    try:
        existing_layers = list_layers(base_path)
    except Exception:
        return results

    layers_to_check = LAYERS_WITH_CLASS
    if layer_filter:
        layers_to_check = [l for l in LAYERS_WITH_CLASS if l.upper() == layer_filter.upper()]

    for layer_name in layers_to_check:
        real_name = find_layer_name(existing_layers, layer_name)
        if real_name is None:
            continue

        gdf = gpd.read_file(base_path, layer=real_name, ignore_geometry=True)

        if len(gdf) == 0:
            continue

        columns = gdf.columns.tolist()
        col_class = next((c for c in columns if c.upper() == "CLASSE"), None)

        if col_class is None:
            continue

        # Check: numeric type
        dtype = gdf[col_class].dtype
        if dtype.kind in ("i", "u", "f"):
            results.append(CheckResult(
                name="CLASSE numeric type",
                status=Status.CONFORMANT,
                details=f"Type: {dtype}",
                category="domain",
                layer=layer_name,
            ))
        else:
            try:
                import pandas as pd
                pd.to_numeric(gdf[col_class], errors="raise")
                results.append(CheckResult(
                    name="CLASSE numeric type",
                    status=Status.NON_CONFORMANT,
                    details=f"Layer '{real_name}': declared type {dtype}, but values are convertible to numeric",
                    category="domain",
                    layer=layer_name,
                ))
            except (ValueError, TypeError):
                results.append(CheckResult(
                    name="CLASSE numeric type",
                    status=Status.NON_CONFORMANT,
                    details=f"Attribute '{col_class}' contains non-numeric values (type: {dtype})",
                    category="domain",
                    layer=layer_name,
                ))
                continue

        # Check: null values
        null_count = gdf[col_class].isna().sum()
        if null_count > 0:
            results.append(CheckResult(
                name="CLASSE null values",
                status=Status.NON_CONFORMANT,
                details=f"{null_count}/{len(gdf)} records with null CLASSE",
                category="domain",
                layer=layer_name,
            ))
        else:
            results.append(CheckResult(
                name="CLASSE null values",
                status=Status.CONFORMANT,
                details="No null values",
                category="domain",
                layer=layer_name,
            ))

        # Check: unique values (informational)
        try:
            unique_values = sorted(gdf[col_class].dropna().unique().tolist())
        except TypeError:
            unique_values = list(gdf[col_class].dropna().unique())
        results.append(CheckResult(
            name="CLASSE values",
            status=Status.CONFORMANT,
            details=f"Values found: {unique_values}",
            category="domain",
            layer=layer_name,
        ))

        # Check: values within expected domain
        domain = CLASS_DOMAIN.get(layer_name.upper())
        if domain and unique_values:
            min_val, max_val = domain
            try:
                numeric_values = [float(v) for v in unique_values]
                out_of_domain = [v for v in numeric_values if v < min_val or v > max_val]
            except (ValueError, TypeError):
                out_of_domain = unique_values

            if out_of_domain:
                results.append(CheckResult(
                    name="CLASSE domain",
                    status=Status.NON_CONFORMANT,
                    details=f"Values outside interval [{min_val}, {max_val}]: {out_of_domain}",
                    category="domain",
                    layer=layer_name,
                ))
            else:
                results.append(CheckResult(
                    name="CLASSE domain",
                    status=Status.CONFORMANT,
                    details=f"All values within interval [{min_val}, {max_val}]",
                    category="domain",
                    layer=layer_name,
                ))

    return results


# ---------------------------------------------------------------------------
# TOPOLOGICAL CONSISTENCY
# ---------------------------------------------------------------------------


def validate_topological_consistency(base_path: Path, progress_callback=None, layer_filter: str | None = None, progress_messages: dict | None = None) -> list[CheckResult]:
    """Checks geometric integrity: nulls, empties, invalids, dimension."""
    results = []
    _pm = progress_messages or {}

    def _progress(pct, msg=""):
        if progress_callback:
            progress_callback(pct, msg)

    try:
        existing_layers = list_layers(base_path)
    except Exception:
        return results

    layers_to_validate = EXPECTED_LAYERS
    if layer_filter:
        layers_to_validate = [layer_filter]

    layers_to_process = []
    for layer_name in layers_to_validate:
        real_name = find_layer_name(existing_layers, layer_name)
        if real_name is not None:
            layers_to_process.append((layer_name, real_name))

    total_layers = len(layers_to_process)
    if total_layers == 0:
        return results

    for idx, (layer_name, real_name) in enumerate(layers_to_process):
        pct_base = 65 + int((idx / total_layers) * 35)
        _progress(pct_base, _pm.get("topo_layer", "Topological consistency: layer {idx}/{total} — {name}").format(
            idx=idx+1, total=total_layers, name=real_name))

        import pyogrio
        layer_info = pyogrio.read_info(str(base_path), layer=real_name)
        geom_type_str = layer_info.get("geometry_type", "") if layer_info else ""
        geom_type_upper = geom_type_str.upper() if geom_type_str else ""

        # Skip topological checks for non-spatial layers (no geometry column).
        # validate_conceptual_consistency already reports "Geometry column missing".
        if not geom_type_str:
            continue

        has_z_or_m = any(dim in geom_type_upper for dim in [" Z", " M", "ZM", "25D"])

        if has_z_or_m:
            results.append(CheckResult(
                name="Geometry dimension",
                status=Status.WARNING,
                details=f"Layer '{real_name}' with type '{geom_type_str}' (expected 2D without Z/M)",
                category="topological",
                layer=layer_name,
            ))
        else:
            results.append(CheckResult(
                name="Geometry dimension",
                status=Status.CONFORMANT,
                details=f"2D geometries — type: {geom_type_str}",
                category="topological",
                layer=layer_name,
            ))

        total = layer_info.get("features", 0) if layer_info else 0
        if total == 0:
            continue

        import time as _time_mod
        import numpy as np
        import shapely

        # FIX 2: hasattr() checks moved outside the batch loop —
        # avoids 5 × N redundant calls (N = number of batches).
        HAS_VECTOR_API    = hasattr(shapely, "is_valid")
        HAS_MAKE_VALID    = hasattr(shapely, "make_valid")
        HAS_IS_VALID_REASON = hasattr(shapely, "is_valid_reason")
        HAS_SET_PRECISION = hasattr(shapely, "set_precision")

        HARD_ERRORS = (
            "Too few points",
            "Holes are nested",
            "Interior is disconnected",
            "Polygon interior is disconnected",
            "Duplicate Rings",
        )
        SKIP_REASONS = ("Ring Self-intersection", "Self-intersection")

        t_start = _time_mod.time()
        BATCH_SIZE = 1000
        null_count = 0
        empty_count = 0
        invalid_count = 0

        for batch_start in range(0, total, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total)

            # FIX 1: progress emitted AFTER reading+processing, not before.
            # UI now shows the count that is actually being processed right now.

            batch_gdf = gpd.read_file(
                base_path, layer=real_name,
                include_fields=[],
                engine="pyogrio",
                skip_features=batch_start,
                max_features=BATCH_SIZE,
            )

            batch_notna = batch_gdf.geometry.notna()
            null_count += (~batch_notna).sum()

            batch_not_empty = ~batch_gdf.geometry.is_empty
            empty_count += (batch_notna & ~batch_not_empty).sum()

            mask_ok = batch_notna & batch_not_empty
            batch_valid = batch_gdf[mask_ok]

            if len(batch_valid) > 0:
                try:
                    geom_arr = batch_valid.geometry.to_numpy()
                except AttributeError:
                    geom_arr = np.asarray(batch_valid.geometry.tolist(), dtype=object)

                if HAS_VECTOR_API:
                    mask_inv = ~shapely.is_valid(geom_arr)
                else:
                    mask_inv = np.asarray([not g.is_valid for g in geom_arr])

                # FIX 4: yield control to Qt event loop after the heaviest
                # Shapely call so the UI stays responsive during large batches.
                if progress_callback:
                    try:
                        from qgis.PyQt.QtCore import QCoreApplication
                        QCoreApplication.processEvents()
                    except Exception:
                        pass

                batch_invalid = 0

                if mask_inv.any():
                    suspect_geoms = geom_arr[mask_inv].tolist()

                    if HAS_IS_VALID_REASON:
                        suspect_reasons = [shapely.is_valid_reason(g) for g in suspect_geoms]
                    else:
                        suspect_reasons = ["Unknown"] * len(suspect_geoms)

                    for geom, reason in zip(suspect_geoms, suspect_reasons):
                        if not HAS_MAKE_VALID and not HAS_SET_PRECISION:
                            batch_invalid += 1
                            continue
                        if any(h in reason for h in HARD_ERRORS):
                            batch_invalid += 1
                        elif any(s in reason for s in SKIP_REASONS):
                            pass  # silently skip self-intersection
                        else:
                            batch_invalid += 1

                invalid_count += batch_invalid

                if invalid_count > 0:
                    # FIX 1: progress update before early exit
                    _progress(pct_base, _pm.get("topo_error_detected",
                        "Topological consistency: {name} — topological error detected, stopping check").format(
                        name=real_name))
                    del batch_gdf, batch_valid
                    break

            # FIX 1: progress emitted here — after the batch is done
            _progress(pct_base, _pm.get("topo_checked",
                "Topological consistency: {name} — {end}/{total} records checked").format(
                name=real_name, end=batch_end, total=total))
            del batch_gdf, batch_valid

        t_elapsed = _time_mod.time() - t_start
        _progress(pct_base, _pm.get("topo_completed", "Topological consistency: {name} — completed in {elapsed:.1f}s").format(
            name=real_name, elapsed=t_elapsed))

        if null_count > 0:
            results.append(CheckResult(
                name="Null geometries",
                status=Status.NON_CONFORMANT,
                details=f"{null_count}/{total} null geometries",
                category="topological",
                layer=layer_name,
            ))
        else:
            results.append(CheckResult(
                name="Null geometries",
                status=Status.CONFORMANT,
                details="No null geometries",
                category="topological",
                layer=layer_name,
            ))

        if empty_count > 0:
            results.append(CheckResult(
                name="Empty geometries",
                status=Status.NON_CONFORMANT,
                details=f"{empty_count}/{total} empty geometries",
                category="topological",
                layer=layer_name,
            ))
        else:
            results.append(CheckResult(
                name="Empty geometries",
                status=Status.CONFORMANT,
                details="No empty geometries",
                category="topological",
                layer=layer_name,
            ))

        if invalid_count > 0:
            results.append(CheckResult(
                name="Topological errors",
                status=Status.NON_CONFORMANT,
                details=f"Layer '{real_name}' has records with topological errors",
                category="topological",
                layer=layer_name,
            ))
        else:
            results.append(CheckResult(
                name="Topological errors",
                status=Status.CONFORMANT,
                details="No topological errors detected",
                category="topological",
                layer=layer_name,
            ))

    return results


def validate_topological_consistency_detailed(base_path: Path, progress_callback=None, layer_filter: str | None = None, error_limit: int | None = None, progress_messages: dict | None = None) -> list[CheckResult]:
    """Detailed topological check — identifies WHICH features have errors."""
    results = []
    _pm = progress_messages or {}

    def _progress(pct, msg=""):
        if progress_callback:
            progress_callback(pct, msg)

    if not layer_filter:
        results.append(CheckResult(
            name="Detailed validation",
            status=Status.NON_CONFORMANT,
            details="Detailed validation requires selecting a specific layer",
            category="topological",
        ))
        return results

    try:
        existing_layers = list_layers(base_path)
    except Exception:
        return results

    real_name = find_layer_name(existing_layers, layer_filter)
    if real_name is None:
        results.append(CheckResult(
            name="Layer not found",
            status=Status.NON_CONFORMANT,
            details=f"Layer '{layer_filter}' not found in dataset",
            category="topological",
            layer=layer_filter,
        ))
        return results

    pct_base = 65
    _progress(pct_base, _pm.get("topo_detail_start", "Detailed topological consistency: {name}").format(name=real_name))

    import pyogrio
    layer_info = pyogrio.read_info(str(base_path), layer=real_name)
    geom_type_str = layer_info.get("geometry_type", "") if layer_info else ""
    geom_type_upper = geom_type_str.upper() if geom_type_str else ""

    # Skip topological checks for non-spatial layers.
    if not geom_type_str:
        results.append(CheckResult(
            name="Geometry column missing",
            status=Status.NON_CONFORMANT,
            details=f"Layer '{real_name}' has no geometry column — topological checks skipped",
            category="topological",
            layer=layer_filter,
        ))
        return results

    has_z_or_m = any(dim in geom_type_upper for dim in [" Z", " M", "ZM", "25D"])

    if has_z_or_m:
        results.append(CheckResult(
            name="Geometry dimension",
            status=Status.WARNING,
            details=f"Layer '{real_name}' with type '{geom_type_str}' (expected 2D without Z/M)",
            category="topological",
            layer=layer_filter,
        ))
    else:
        results.append(CheckResult(
            name="Geometry dimension",
            status=Status.CONFORMANT,
            details=f"2D geometries — type: {geom_type_str}",
            category="topological",
            layer=layer_filter,
        ))

    total = layer_info.get("features", 0) if layer_info else 0
    if total == 0:
        return results

    import time as _time_mod
    import numpy as np
    import shapely

    # FIX 2: hasattr() checks moved outside the batch loop.
    HAS_VECTOR_API      = hasattr(shapely, "is_valid")
    HAS_MAKE_VALID      = hasattr(shapely, "make_valid")
    HAS_IS_VALID_REASON = hasattr(shapely, "is_valid_reason")
    HAS_SET_PRECISION   = hasattr(shapely, "set_precision")
    HAS_EQUALS_EXACT    = hasattr(shapely, "equals_exact")

    HARD_ERRORS = (
        "Too few points",
        "Holes are nested",
        "Interior is disconnected",
        "Polygon interior is disconnected",
        "Duplicate Rings",
    )

    t_start = _time_mod.time()
    BATCH_SIZE = 1000
    null_count = 0
    empty_count = 0
    detailed_errors = []
    limit_reached = False

    for batch_start in range(0, total, BATCH_SIZE):
        if limit_reached:
            break

        batch_end = min(batch_start + BATCH_SIZE, total)

        # FIX 1: progress emitted AFTER batch processing, not before.

        batch_gdf = gpd.read_file(
            base_path, layer=real_name,
            include_fields=[],
            engine="pyogrio",
            skip_features=batch_start,
            max_features=BATCH_SIZE,
            fid_as_index=True,
        )
        if not getattr(batch_gdf.index, 'name', None) == 'fid':
            batch_gdf = batch_gdf.reset_index(drop=True)

        batch_notna = batch_gdf.geometry.notna()
        batch_null = (~batch_notna).sum()
        null_count += batch_null

        if batch_null > 0:
            for pos, (df_idx, flag) in enumerate(zip(batch_gdf.index, batch_notna)):
                if not flag:
                    detailed_errors.append({"fid": df_idx, "error": "Null geometry (NULL)", "wkt": ""})

        batch_not_empty = ~batch_gdf.geometry.is_empty
        batch_empty = (batch_notna & ~batch_not_empty).sum()
        empty_count += batch_empty

        if batch_empty > 0:
            for df_idx, (is_notna, is_not_empty) in zip(
                batch_gdf.index, zip(batch_notna, batch_not_empty)
            ):
                if is_notna and not is_not_empty:
                    geom = batch_gdf.geometry.loc[df_idx]
                    wkt_str = geom.wkt if geom is not None else ""
                    detailed_errors.append({"fid": df_idx, "error": "Empty geometry (EMPTY)", "wkt": wkt_str})

        mask_ok = batch_notna & batch_not_empty
        batch_valid = batch_gdf[mask_ok]

        if len(batch_valid) > 0:
            try:
                geom_arr = batch_valid.geometry.to_numpy()
            except AttributeError:
                geom_arr = np.asarray(batch_valid.geometry.tolist(), dtype=object)

            if HAS_VECTOR_API:
                mask_inv = ~shapely.is_valid(geom_arr)
            else:
                mask_inv = np.asarray([not g.is_valid for g in geom_arr])

            # FIX 4: yield to Qt event loop after the heaviest Shapely call.
            if progress_callback:
                try:
                    from qgis.PyQt.QtCore import QCoreApplication
                    QCoreApplication.processEvents()
                except Exception:
                    pass

            if mask_inv.any():
                suspect_indices = batch_valid.index[mask_inv].tolist()
                suspect_geoms_arr = geom_arr[mask_inv]

                if HAS_IS_VALID_REASON:
                    suspect_reasons = [shapely.is_valid_reason(g) for g in suspect_geoms_arr]
                else:
                    suspect_reasons = ["Unknown"] * len(suspect_geoms_arr)

                for real_fid, geom, reason in zip(
                    suspect_indices, suspect_geoms_arr, suspect_reasons
                ):
                    geom_wkt = (
                        batch_gdf.geometry.loc[real_fid].wkt
                        if batch_gdf.geometry.loc[real_fid] is not None
                        else ""
                    )

                    if not HAS_MAKE_VALID and not HAS_SET_PRECISION:
                        detailed_errors.append({
                            "fid": real_fid,
                            "error": "Invalid geometry (reason unavailable — Shapely < 2.0)",
                            "wkt": geom_wkt,
                            "si_type": None,
                            "severity": "ERROR",
                        })
                    elif any(h in reason for h in HARD_ERRORS):
                        detailed_errors.append({
                            "fid": real_fid,
                            "error": reason,
                            "wkt": geom_wkt,
                            "si_type": None,
                            "severity": "ERROR",
                        })
                    elif "Ring Self-intersection" in reason or "Self-intersection" in reason:
                        pass  # silently skip self-intersection
                    else:
                        detailed_errors.append({
                            "fid": real_fid,
                            "error": reason,
                            "wkt": geom_wkt,
                            "si_type": None,
                            "severity": "ERROR",
                        })

                    topo_errors_so_far = sum(
                        1 for e in detailed_errors
                        if "null" not in e["error"].lower()
                        and "empty" not in e["error"].lower()
                        and e.get("severity", "ERROR") == "ERROR"
                    )
                    if error_limit is not None and topo_errors_so_far >= error_limit:
                        _progress(
                            pct_base + int((batch_end / total) * 35),
                            _pm.get("topo_detail_limit",
                                "Detailed topological consistency: {name} — limit of {limit} error(s) reached, stopping").format(
                                name=real_name, limit=error_limit)
                        )
                        limit_reached = True
                        break

        # FIX 1: progress emitted here — after the batch is fully processed
        _progress(
            pct_base + int((batch_end / total) * 35),
            _pm.get("topo_detail_checked",
                "Detailed topological consistency: {name} — {end}/{total} records checked").format(
                name=real_name, end=batch_end, total=total)
        )
        del batch_gdf, batch_valid

    t_elapsed = _time_mod.time() - t_start
    _progress(100, _pm.get("topo_detail_completed", "Detailed topological consistency: {name} — completed in {elapsed:.1f}s").format(
        name=real_name, elapsed=t_elapsed))

    if null_count > 0:
        results.append(CheckResult(name="Null geometries", status=Status.NON_CONFORMANT, details=f"{null_count}/{total} null geometries", category="topological", layer=layer_filter))
    else:
        results.append(CheckResult(name="Null geometries", status=Status.CONFORMANT, details="No null geometries", category="topological", layer=layer_filter))

    if empty_count > 0:
        results.append(CheckResult(name="Empty geometries", status=Status.NON_CONFORMANT, details=f"{empty_count}/{total} empty geometries", category="topological", layer=layer_filter))
    else:
        results.append(CheckResult(name="Empty geometries", status=Status.CONFORMANT, details="No empty geometries", category="topological", layer=layer_filter))

    topological_errors = [
        e for e in detailed_errors
        if "null" not in e["error"].lower() and "empty" not in e["error"].lower()
    ]

    # Partition by severity: Ring SI warnings are reported separately
    hard_errors   = [e for e in topological_errors if e.get("severity", "ERROR") == "ERROR"]
    ring_warnings = [e for e in topological_errors if e.get("severity", "ERROR") == "WARNING"]

    if hard_errors:
        # Use a translatable suffix pattern for the limit message.
        # The detail_patterns translator will convert this to the active locale.
        limit_suffix = (
            f" (showing {len(topological_errors)} of max {error_limit}, processing stopped early)"
            if limit_reached else ""
        )
        results.append(CheckResult(
            name="Topological errors",
            status=Status.NON_CONFORMANT,
            details=f"{len(hard_errors)} geometry(ies) with topological errors{limit_suffix}",
            category="topological",
            layer=layer_filter,
        ))
        for error in hard_errors:
            results.append(CheckResult(
                name=f"Error in feature FID {error['fid']}",
                status=Status.NON_CONFORMANT,
                details=error["error"],
                category="topological",
                layer=layer_filter,
                wkt=error.get("wkt", ""),
            ))
    else:
        results.append(CheckResult(
            name="Topological errors",
            status=Status.CONFORMANT,
            details="No topological errors detected",
            category="topological",
            layer=layer_filter,
        ))

    # [CHANGE 4] Ring SI warnings block removed — self-intersection
    # errors are not reported. ring_classifier.py remains available
    # for future use but is not called in normal validation flow.

    null_empty_errors = [
        e for e in detailed_errors
        if "null" in e["error"].lower() or "empty" in e["error"].lower()
    ]
    for error in null_empty_errors:
        results.append(CheckResult(
            name=f"Error in feature FID {error['fid']}",
            status=Status.NON_CONFORMANT,
            details=error["error"],
            category="topological",
            layer=layer_filter,
            wkt=error.get("wkt", ""),
        ))

    return results


# ---------------------------------------------------------------------------
# Main validation function
# ---------------------------------------------------------------------------


def validate_dataset(base_path: str | Path, progress_callback=None, layer_filter: str | None = None, detailed: bool = False, error_limit: int | None = None, progress_messages: dict | None = None) -> ValidationReport:
    """
    Runs all logical consistency validations (ISO 19157)
    on the geographic dataset and returns the report.

    Parameters:
        base_path: path to the .gpkg file or .gdb directory
        progress_callback: optional callback(percent, message) to update progress bar
        layer_filter: name of a specific layer to validate (None = all)
        detailed: if True, uses detailed topological validation
        error_limit: maximum number of topological errors to report
        progress_messages: optional dict of localised progress message templates
                           (obtained via I18n.get_progress_messages())

    Returns:
        ValidationReport with all executed checks
    """
    import time as _time

    base_path = Path(base_path)
    _log_entries = []

    # Use provided message templates or fall back to English defaults
    _pm = progress_messages or {}

    def _progress(pct, msg=""):
        if progress_callback:
            progress_callback(pct, msg)

    def _log(msg):
        ts = _time.strftime("%H:%M:%S")
        _log_entries.append(f"[{ts}] {msg}")
        _progress(-1, msg)

    if not base_path.exists():
        report = ValidationReport(file_path=str(base_path))
        report.checks.append(CheckResult(
            name="File",
            status=Status.NON_CONFORMANT,
            details=f"File not found: {base_path}",
            category="format",
        ))
        return report

    _temp_dir = None
    original_path = base_path
    if base_path.suffix.lower() == ".zip" and base_path.is_file():
        _progress(0, _pm.get("extracting_zip", "Extracting GPKG from ZIP archive..."))
        extracted = extract_gpkg_from_zip(base_path)
        if extracted and extracted.exists():
            _temp_dir = extracted.parent
            base_path = extracted
            _progress(5, _pm.get("gpkg_extracted", "GPKG extracted: {name}").format(name=extracted.name))
        else:
            report = ValidationReport(file_path=str(original_path))
            report.checks.append(CheckResult(
                name="Dataset format",
                status=Status.NON_CONFORMANT,
                details="ZIP file contains no GeoPackage (.gpkg)",
                category="format",
            ))
            return report

    report = ValidationReport(file_path=str(original_path))

    # 1. Format consistency (0-10%)
    _progress(0, _pm.get("checking_format", "Checking format..."))
    format_checks = validate_format(base_path)
    report.checks.extend(format_checks)
    _progress(10, _pm.get("format_checked", "Format checked ({n} checks)").format(n=len(format_checks)))

    if any(c.status == Status.NON_CONFORMANT for c in format_checks):
        _progress(100, _pm.get("completed_invalid_format", "Completed (invalid format)"))
        report.log = _log_entries
        return report

    # Guard: if the base is readable but has zero layers, there is nothing
    # to validate in the subsequent phases — report and stop gracefully.
    readability_check = next(
        (c for c in format_checks if c.name == "Dataset readability"), None
    )
    if readability_check and readability_check.status == Status.CONFORMANT:
        # Extract layer count from the details string "Dataset readable, N layer(s) found"
        import re as _re
        _m = _re.search(r"(\d+) layer", readability_check.details)
        _layer_count = int(_m.group(1)) if _m else -1
        if _layer_count == 0:
            _progress(100, _pm.get("completed_invalid_format", "Completed (invalid format)"))
            report.log = _log_entries
            return report

    # 2. Conceptual consistency (10-40%)
    _progress(15, _pm.get("checking_conceptual", "Checking conceptual consistency..."))
    report.checks.extend(validate_conceptual_consistency(base_path, layer_filter=layer_filter))
    _progress(40, _pm.get("conceptual_checked", "Conceptual consistency checked"))

    # 3. Domain consistency (40-60%)
    _progress(45, _pm.get("checking_domain", "Checking domain consistency..."))
    report.checks.extend(validate_domain_consistency(base_path, layer_filter=layer_filter))
    _progress(60, _pm.get("domain_checked", "Domain consistency checked"))

    # 4. Topological consistency (60-100%)
    _progress(65, _pm.get("checking_topological", "Checking topological consistency..."))
    if detailed and layer_filter:
        report.checks.extend(validate_topological_consistency_detailed(
            base_path, progress_callback=progress_callback,
            layer_filter=layer_filter, error_limit=error_limit,
            progress_messages=_pm,
        ))
    else:
        report.checks.extend(validate_topological_consistency(
            base_path, progress_callback=progress_callback,
            layer_filter=layer_filter, progress_messages=_pm,
        ))
    _progress(100, _pm.get("validation_complete", "Validation complete"))

    if _temp_dir:
        import shutil
        try:
            shutil.rmtree(_temp_dir, ignore_errors=True)
        except Exception:
            pass

    report.log = _log_entries
    return report


# Backward compatibility alias
validate_gpkg = validate_dataset
# Legacy Portuguese alias kept for any external code that may reference it
validar_base = validate_dataset


# ---------------------------------------------------------------------------
# PDF report export — Padrão Digital de Governo (GOV.BR DS)
# ---------------------------------------------------------------------------


def _load_logo_base64(file_name: str) -> tuple[str, str]:
    """
    Loads an image from the assets/ directory and returns (base64_data, mime_type).
    Returns ("", "") if the file does not exist.
    """
    import base64

    logo_path = _os.path.join(_os.path.dirname(__file__), "assets", file_name)
    if not _os.path.isfile(logo_path):
        return "", ""
    try:
        ext = _os.path.splitext(file_name)[1].lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
        mime_type = mime_map.get(ext, "image/png")
        with open(logo_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode("utf-8"), mime_type
    except Exception:
        return "", ""


def export_report_pdf(report: ValidationReport, output_path: str | Path, locale: str = "en_US") -> Path:
    """
    Generates a PDF report with GOV.BR DS visual style.

    Includes SFB and SICAR logos (if available in assets/).
    Uses QTextDocument + QPrinter from Qt (available in QGIS).

    Parameters:
        report: executed validation report
        output_path: path of the output PDF file
        locale: display locale ("en_US" or "pt_BR")

    Returns:
        Path of the generated PDF file
    """
    from qgis.PyQt.QtCore import QMarginsF
    from qgis.PyQt.QtGui import QPageLayout, QPageSize, QTextDocument
    from qgis.PyQt.QtPrintSupport import QPrinter

    output_path = Path(output_path)
    html = _generate_report_html(report, locale=locale)

    try:
        _HighRes = QPrinter.PrinterMode.HighResolution
    except AttributeError:
        _HighRes = QPrinter.HighResolution

    try:
        _PdfFormat = QPrinter.OutputFormat.PdfFormat
    except AttributeError:
        _PdfFormat = QPrinter.PdfFormat

    try:
        _Point = QPrinter.Unit.Point
    except AttributeError:
        _Point = QPrinter.Point

    try:
        _A4 = QPageSize.PageSizeId.A4
    except AttributeError:
        _A4 = QPageSize.A4

    try:
        _Portrait = QPageLayout.Orientation.Portrait
    except AttributeError:
        _Portrait = QPageLayout.Portrait

    printer = QPrinter(_HighRes)
    printer.setOutputFormat(_PdfFormat)
    printer.setOutputFileName(str(output_path))
    page_layout = QPageLayout(QPageSize(_A4), _Portrait, QMarginsF(15, 15, 15, 15))
    printer.setPageLayout(page_layout)

    doc = QTextDocument()
    doc.setHtml(html)
    doc.setPageSize(printer.pageRect(_Point).size())
    print_fn = getattr(doc, 'print_', None) or getattr(doc, 'print')
    print_fn(printer)

    return output_path


def _generate_report_html(report: ValidationReport, locale: str = "en_US") -> str:
    """
    Generates the formatted HTML content of the report in GOV.BR DS style.
    Supports locale "en_US" and "pt_BR".
    """
    # -----------------------------------------------------------------------
    # Inline translation tables (keeps validator.py self-contained)
    # -----------------------------------------------------------------------
    _status_lbl = {
        "en_US": {"CONFORMANT": "CONFORMANT", "NON-CONFORMANT": "NON-CONFORMANT", "WARNING": "WARNING"},
        "pt_BR": {"CONFORMANT": "EM CONFORMIDADE", "NON-CONFORMANT": "EM DIVERGÊNCIA", "WARNING": "AVISO"},
    }.get(locale, {})

    _name_lbl = {
        "pt_BR": {
            "Dataset format": "Formato da base", "Dataset readability": "Leitura da base",
            "File": "Arquivo", "Layer names": "Nomes de camadas", "Missing layer": "Camada faltante",
            "Records": "Registros", "CLASSE attribute": "Atributo CLASSE",
            "Absence of CLASSE": "Ausência de CLASSE", "CRS": "CRS",
            "Layer listing": "Leitura de camadas", "CLASSE numeric type": "Tipo numérico de CLASSE",
            "CLASSE null values": "Valores nulos de CLASSE", "CLASSE values": "Valores de CLASSE",
            "CLASSE domain": "Domínio de CLASSE", "Geometry dimension": "Dimensão das geometrias",
            "Null geometries": "Geometrias nulas", "Empty geometries": "Geometrias vazias",
            "Topological errors": "Erros topológicos",
        }
    }.get(locale, {})

    _detail_lbl = {
        "pt_BR": {
            "Valid format: GeoPackage (.gpkg)": "Formato válido: GeoPackage (.gpkg)",
            "Valid format: ESRI GeoDatabase (.gdb)": "Formato válido: ESRI GeoDatabase (.gdb)",
            "Valid format: Compressed GeoPackage (.gpkg.zip)": "Formato válido: GeoPackage compactado (.gpkg.zip)",
            "Accepted formats: GeoPackage (.gpkg), ESRI GeoDatabase (.gdb)":
                "Formatos aceitos: GeoPackage (.gpkg), ESRI GeoDatabase (.gdb)",
            "No CLASSE attribute (correct)": "Não possui atributo CLASSE (correto)",
            "Could not list dataset layers": "Não foi possível listar as camadas da base",
            "CRS not defined": "CRS não definido",
            "No null values": "Nenhum valor nulo",
            "Values found:": "Valores encontrados:",
            "All values within interval": "Todos os valores dentro do intervalo",
            "Values outside interval": "Valores fora do intervalo",
            "Type:": "Tipo:",
            "No null geometries": "Nenhuma geometria nula",
            "No empty geometries": "Nenhuma geometria vazia",
            "No topological errors detected": "Nenhum erro topológico detectado",
            "Null geometry (NULL)": "Geometria nula (NULL)",
            "Empty geometry (EMPTY)": "Geometria vazia (EMPTY)",
            "2D geometries — type:": "Geometrias bidimensionais (2D) — tipo:",
        }
    }.get(locale, {})

    _ui = {
        "en_US": {
            "title": "SICAR AD — Validate Environmental Dataset Structure",
            "subtitle": "Conformance Assessment based on ISO 19157:2013",
            "val_date": "Validation date", "source": "Source",
            "val_result": "Validation result",
            "summary_lbl": "Summary",
            "sum_by_cat": "Summary by Category",
            "layers_found": "Layers found in dataset",
            "non_conf_items": "Non-conformant items",
            "warn_items": "Warning items",
            "cat_format": "Format Consistency", "cat_conceptual": "Conceptual Consistency",
            "cat_domain": "Domain Consistency", "cat_topological": "Topological Consistency",
            "col_layer": "Layer", "col_check": "Check", "col_status": "Status",
            "col_details": "Details", "col_category": "Category", "col_result": "Result",
            "st_conf": "✓ Conformant", "st_warn": "⚠ Warning", "st_nonconf": "✗ Non-conformant",
            "conformant_of": "conformant",
            "badge_conf": "CONFORMANT", "badge_warn": "CONFORMANT WITH WARNINGS", "badge_nonconf": "NON-CONFORMANT",
            "rules_executed": "{total} rules executed ({ok} conformant",
            "non_conformant": ", {n} non-conformant", "warnings_": ", {n} warning(s)", "close": ")",
            "footer": "Brazilian Forest Service — SFB &nbsp;|&nbsp; National Rural Environmental Registry — SICAR<br>"
                      "Report automatically generated by SICAR AD plugin — Validate Environmental Dataset Structure<br>"
                      "Digital Government Standard · gov.br",
        },
        "pt_BR": {
            "title": "SICAR AD — Validar Estrutura da Base Ambiental",
            "subtitle": "Avaliação de Conformidade com base na ISO 19157:2013",
            "val_date": "Data da validação", "source": "Fonte",
            "val_result": "Resultado da validação",
            "summary_lbl": "Resumo",
            "sum_by_cat": "Resumo por Categoria",
            "layers_found": "Camadas encontradas na base",
            "non_conf_items": "Itens em Divergência",
            "warn_items": "Itens com Aviso",
            "cat_format": "Consistência de Formato", "cat_conceptual": "Consistência Conceitual",
            "cat_domain": "Consistência de Domínio", "cat_topological": "Consistência Topológica",
            "col_layer": "Camada", "col_check": "Verificação", "col_status": "Status",
            "col_details": "Detalhes", "col_category": "Categoria", "col_result": "Resultado",
            "st_conf": "✓ Conforme", "st_warn": "⚠ Aviso", "st_nonconf": "✗ Divergente",
            "conformant_of": "em conformidade",
            "badge_conf": "EM CONFORMIDADE", "badge_warn": "EM CONFORMIDADE, MAS COM AVISO", "badge_nonconf": "EM DIVERGÊNCIA",
            "rules_executed": "{total} regras executadas ({ok} em conformidade",
            "non_conformant": ", {n} em divergência", "warnings_": ", {n} aviso(s)", "close": ")",
            "footer": "Serviço Florestal Brasileiro — SFB &nbsp;|&nbsp; Sistema Nacional de Cadastro Ambiental Rural — SICAR<br>"
                      "Relatório gerado automaticamente pelo plugin SICAR AD — Validar Estrutura da Base Ambiental<br>"
                      "Padrão Digital de Governo · gov.br",
        },
    }.get(locale, {})

    def _tn(name):
        return _name_lbl.get(name, name)

    def _td(detail):
        if detail in _detail_lbl:
            return _detail_lbl[detail]
        for k, v in _detail_lbl.items():
            if detail.startswith(k):
                return v + detail[len(k):]
        return detail

    def _ts(status_val):
        return _status_lbl.get(status_val, status_val)

    def _summary_text():
        total = len(report.checks)
        ok = sum(1 for c in report.checks if c.status == Status.CONFORMANT)
        non_conf = sum(1 for c in report.checks if c.status == Status.NON_CONFORMANT)
        warnings = sum(1 for c in report.checks if c.status == Status.WARNING)
        parts = [_ui["rules_executed"].format(total=total, ok=ok)]
        if non_conf:
            parts.append(_ui["non_conformant"].format(n=non_conf))
        if warnings:
            parts.append(_ui["warnings_"].format(n=warnings))
        parts.append(_ui["close"])
        return "".join(parts)

    # -----------------------------------------------------------------------
    file_name = Path(report.file_path).name
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")

    SURFACE_DARK = "#071D41"; SURFACE_ALT = "#F8F8F8"; TEXT_PRIMARY = "#333333"
    TEXT_SECONDARY = "#636363"; INTERACTIVE = "#1351B4"; SUCCESS = "#168821"
    SUCCESS_BG = "#E3F5E1"; ERROR = "#E52207"; ERROR_BG = "#FDE0DB"
    WARNING = "#D2600F"; WARNING_BG = "#FFF5C2"; BORDER = "#CCCCCC"
    BORDER_LIGHT = "#E6E6E6"; FONT = "Rawline, Roboto, Arial, sans-serif"

    logo_sfb_b64, logo_sfb_mime = _load_logo_base64("sfb_logo.png")
    logo_sicar_b64, logo_sicar_mime = _load_logo_base64("sicar_logo_v2.png")
    logo_sfb_html = f"<img src='data:{logo_sfb_mime};base64,{logo_sfb_b64}' height='36' style='margin-right: 8px;'>" if logo_sfb_b64 else ""
    logo_sicar_html = f"<img src='data:{logo_sicar_mime};base64,{logo_sicar_b64}' height='30' style='margin-left: 8px;'>" if logo_sicar_b64 else ""

    if report.passed and not report.has_warnings:
        badge_bg, badge_border, badge_text, badge_color = SUCCESS_BG, SUCCESS, _ui["badge_conf"], SUCCESS
    elif report.passed and report.has_warnings:
        badge_bg, badge_border, badge_text, badge_color = WARNING_BG, WARNING, _ui["badge_warn"], WARNING
    else:
        badge_bg, badge_border, badge_text, badge_color = ERROR_BG, ERROR, _ui["badge_nonconf"], ERROR

    # Category map (engine keys → locale labels)
    cat_map = {
        "Format Consistency":      _ui["cat_format"],
        "Conceptual Consistency":  _ui["cat_conceptual"],
        "Domain Consistency":      _ui["cat_domain"],
        "Topological Consistency": _ui["cat_topological"],
    }

    html_parts = []
    html_parts.append(f"<html><head><meta charset='utf-8'></head><body style='font-size: 9pt; font-family: {FONT}; color: {TEXT_PRIMARY}; margin: 0; padding: 0;'>")

    html_parts.append(
        f"<table width='100%' cellpadding='0' cellspacing='0' style='margin-bottom: 12px;'><tr>"
        f"<td width='15%' style='vertical-align: middle;'>{logo_sfb_html}</td>"
        f"<td style='text-align: center; vertical-align: middle;'>"
        f"<span style='font-size: 11pt; font-weight: 600; color: {TEXT_PRIMARY};'>{_ui['title']}</span><br>"
        f"<span style='font-size: 8pt; color: {TEXT_SECONDARY};'>{_ui['subtitle']}</span>"
        f"</td>"
        f"<td width='15%' style='text-align: right; vertical-align: middle;'>{logo_sicar_html}</td>"
        f"</tr></table>"
        f"<hr style='border: none; border-top: 2px solid {BORDER_LIGHT}; margin: 0 0 12px 0;'>"
    )

    html_parts.append(
        f"<table width='100%' style='font-size: 8pt; color: {TEXT_SECONDARY}; margin-bottom: 12px;'>"
        f"<tr><td><b>{_ui['val_date']}:</b> {date_str}</td>"
        f"<td style='text-align: right;'><b>{_ui['source']}:</b> {file_name}</td></tr></table>"
    )

    html_parts.append(
        f"<div style='background: {badge_bg}; border-left: 4px solid {badge_border}; padding: 10px 16px; margin-bottom: 16px;'>"
        f"<span style='font-size: 8pt; color: {TEXT_SECONDARY}; font-weight: 600;'>{_ui['val_result']}: </span>"
        f"<span style='font-size: 8pt; font-weight: 700; color: {badge_color};'>{badge_text}</span><br>"
        f"<span style='font-size: 8pt; color: {TEXT_SECONDARY};'><b>{_ui['summary_lbl']}:</b> {_summary_text()}</span></div>"
    )

    # Summary by category table
    html_parts.append(
        f"<h4 style='color: {INTERACTIVE}; font-size: 10pt; font-weight: 600; margin: 12px 0 6px 0; border-bottom: 2px solid {INTERACTIVE}; padding-bottom: 4px;'>{_ui['sum_by_cat']}</h4>"
        f"<table cellpadding='5' cellspacing='0' width='100%' style='border-collapse: collapse; font-size: 8pt; margin-bottom: 12px;'>"
        f"<tr style='background: {SURFACE_ALT};'>"
        f"<th style='text-align: left; border-bottom: 2px solid {BORDER}; padding: 6px 8px;'>{_ui['col_category']}</th>"
        f"<th style='text-align: left; border-bottom: 2px solid {BORDER}; padding: 6px 8px;'>{_ui['col_status']}</th>"
        f"<th style='text-align: left; border-bottom: 2px solid {BORDER}; padding: 6px 8px;'>{_ui['col_result']}</th></tr>"
    )
    for cat_name, info in report.summary_by_category().items():
        cat_label = cat_map.get(cat_name, cat_name)
        if info["status"] == Status.CONFORMANT:
            st_html = f"<span style='color: {SUCCESS}; font-weight: 600;'>{_ui['st_conf']}</span>"
            row_bg = ""
        elif info["status"] == Status.WARNING:
            st_html = f"<span style='color: {WARNING}; font-weight: 600;'>{_ui['st_warn']}</span>"
            row_bg = f" style='background: {WARNING_BG};'"
        else:
            st_html = f"<span style='color: {ERROR}; font-weight: 600;'>{_ui['st_nonconf']}</span>"
            row_bg = f" style='background: {ERROR_BG};'"
        html_parts.append(
            f"<tr{row_bg}><td style='padding: 6px 8px; border-bottom: 1px solid {BORDER_LIGHT};'>{cat_label}</td>"
            f"<td style='padding: 6px 8px; border-bottom: 1px solid {BORDER_LIGHT};'>{st_html}</td>"
            f"<td style='padding: 6px 8px; border-bottom: 1px solid {BORDER_LIGHT};'>{info['conformant']}/{info['total']} {_ui['conformant_of']}</td></tr>"
        )
    html_parts.append("</table>")

    # Layers found
    try:
        layers_found = list_layers(Path(report.file_path))
        html_parts.append(
            f"<h4 style='color: {INTERACTIVE}; font-size: 10pt; font-weight: 600; margin: 12px 0 6px 0; border-bottom: 2px solid {INTERACTIVE}; padding-bottom: 4px;'>{_ui['layers_found']}</h4>"
            f"<div style='font-size: 8pt; padding: 8px 12px; border: 1px solid {BORDER_LIGHT}; margin-bottom: 12px;'>"
        )
        for lyr in layers_found:
            is_expected = any(lyr.upper() == exp.upper() for exp in EXPECTED_LAYERS)
            if is_expected:
                html_parts.append(f"<div style='padding: 2px 0;'><span style='color: {SUCCESS}; font-weight: 600;'>●</span> <b style='color: {SUCCESS};'>{lyr}</b></div>")
            else:
                html_parts.append(f"<div style='padding: 2px 0;'><span style='color: {BORDER};'>●</span> <span style='color: {TEXT_SECONDARY};'>{lyr}</span></div>")
        html_parts.append("</div><br>")
    except Exception:
        pass

    # Non-conformant items
    non_conformant = [c for c in report.checks if c.status == Status.NON_CONFORMANT]
    if non_conformant:
        html_parts.append(
            f"<div style='background: {ERROR_BG}; border-left: 4px solid {ERROR}; padding: 10px 16px; margin-bottom: 16px;'>"
            f"<b style='color: {ERROR}; font-size: 9pt;'>{_ui['non_conf_items']} ({len(non_conformant)})</b>"
            f"<ul style='font-size: 7pt; margin: 4px 0; padding-left: 16px;'>"
        )
        for check in non_conformant:
            layer_txt = f" [{check.layer}]" if check.layer else ""
            html_parts.append(f"<li><b>{_tn(check.name)}</b>{layer_txt}: {_td(check.details)}</li>")
        html_parts.append("</ul></div>")

    # Warning items
    warnings_list = [c for c in report.checks if c.status == Status.WARNING]
    if warnings_list:
        html_parts.append(
            f"<div style='background: {WARNING_BG}; border-left: 4px solid {WARNING}; padding: 10px 16px; margin-bottom: 16px;'>"
            f"<b style='color: {WARNING}; font-size: 9pt;'>{_ui['warn_items']} ({len(warnings_list)})</b>"
            f"<ul style='font-size: 7pt; margin: 4px 0; padding-left: 16px;'>"
        )
        for check in warnings_list:
            layer_txt = f" [{check.layer}]" if check.layer else ""
            html_parts.append(f"<li><b>{_tn(check.name)}</b>{layer_txt}: {_td(check.details)}</li>")
        html_parts.append("</ul></div>")

    # Detail tables by category
    categories = [
        (_ui["cat_format"],      report.format_checks),
        (_ui["cat_conceptual"],  report.conceptual_checks),
        (_ui["cat_domain"],      report.domain_checks),
        (_ui["cat_topological"], report.topological_checks),
    ]
    for cat_name, checks in categories:
        if not checks:
            continue
        html_parts.append(
            f"<h4 style='color: {INTERACTIVE}; font-size: 10pt; font-weight: 600; margin: 16px 0 6px 0; border-bottom: 2px solid {INTERACTIVE}; padding-bottom: 4px;'>{cat_name}</h4>"
            f"<table cellpadding='4' cellspacing='0' width='100%' style='border-collapse: collapse; font-size: 7pt; margin-bottom: 8px;'>"
            f"<tr style='background: {SURFACE_ALT};'>"
            f"<th style='text-align: left; border-bottom: 2px solid {BORDER}; padding: 5px 6px;' width='20%'>{_ui['col_layer']}</th>"
            f"<th style='text-align: left; border-bottom: 2px solid {BORDER}; padding: 5px 6px;' width='16%'>{_ui['col_check']}</th>"
            f"<th style='text-align: left; border-bottom: 2px solid {BORDER}; padding: 5px 6px;' width='14%'>{_ui['col_status']}</th>"
            f"<th style='text-align: left; border-bottom: 2px solid {BORDER}; padding: 5px 6px;' width='50%'>{_ui['col_details']}</th></tr>"
        )
        for idx, check in enumerate(checks):
            row_bg = f" style='background: {SURFACE_ALT};'" if idx % 2 == 1 else ""
            if check.status == Status.CONFORMANT:
                st_td = f"<td style='color: {SUCCESS}; font-weight: 600; padding: 4px 6px; border-bottom: 1px solid {BORDER_LIGHT};'>{_ui['st_conf']}</td>"
            elif check.status == Status.WARNING:
                st_td = f"<td style='color: {WARNING}; font-weight: 600; padding: 4px 6px; border-bottom: 1px solid {BORDER_LIGHT};'>{_ui['st_warn']}</td>"
            else:
                st_td = f"<td style='color: {ERROR}; font-weight: 600; padding: 4px 6px; border-bottom: 1px solid {BORDER_LIGHT};'>{_ui['st_nonconf']}</td>"
            html_parts.append(
                f"<tr{row_bg}>"
                f"<td style='padding: 4px 6px; border-bottom: 1px solid {BORDER_LIGHT};'>{check.layer}</td>"
                f"<td style='padding: 4px 6px; border-bottom: 1px solid {BORDER_LIGHT};'>{_tn(check.name)}</td>"
                f"{st_td}"
                f"<td style='padding: 4px 6px; border-bottom: 1px solid {BORDER_LIGHT};'>{_td(check.details)}</td></tr>"
            )
        html_parts.append("</table>")

    # Institutional footer
    html_parts.append(
        f"<div style='margin-top: 24px; border-top: 2px solid {BORDER_LIGHT}; padding-top: 8px; font-size: 7pt; color: {TEXT_SECONDARY}; text-align: center;'>"
        f"{_ui['footer']}"
        f"</div>"
    )
    html_parts.append("</body></html>")
    return "\n".join(html_parts)


# ---------------------------------------------------------------------------
# Standalone CLI (for testing without QGIS)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python validator.py <file.gpkg|directory.gdb>")
        sys.exit(1)

    base_file = Path(sys.argv[1])
    report = validate_dataset(base_file)

    print(f"\n{'='*70}")
    print("ISO 19157:2013 - LOGICAL CONSISTENCY VALIDATION")
    print(f"File: {report.file_path}")
    print(f"{'='*70}")

    categories = [
        ("FORMAT CONSISTENCY", report.format_checks),
        ("CONCEPTUAL CONSISTENCY", report.conceptual_checks),
        ("DOMAIN CONSISTENCY", report.domain_checks),
        ("TOPOLOGICAL CONSISTENCY", report.topological_checks),
    ]

    for cat_name, checks in categories:
        if not checks:
            continue
        print(f"\n{'-'*70}")
        print(f"  {cat_name}")
        print(f"{'-'*70}")
        for check in checks:
            icon = "[OK]" if check.status == Status.CONFORMANT else \
                   "[!]" if check.status == Status.WARNING else "[X]"
            layer_txt = f" [{check.layer}]" if check.layer else ""
            print(f"  {icon} [{check.status.value:>15}]{layer_txt} {check.name}: {check.details}")

    print(f"\n{'='*70}")
    print(f"  RESULT: {'PASSED' if report.passed else 'FAILED'}")
    print(f"  {report.summary()}")
    print(f"{'='*70}\n")
