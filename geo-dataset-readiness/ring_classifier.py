# -*- coding: utf-8 -*-
# Copyright (C) 2026 Dataprev
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""
ring_classifier.py — Ring Self-Intersection Type Classifier (vectorised)

Classifies GEOS "Ring Self-intersection" errors into semantic subtypes,
distinguishing genuine topological errors from tolerance artefacts.

Performance design:
  - Cheap checks (coordinate inspection via NumPy) run BEFORE make_valid.
    If a cheap check fires, make_valid is never called.
  - make_valid + area are called vectorised over all suspects at once via
    classify_batch(), avoiding per-geometry Python overhead.
  - No pure-Python loops over coordinates: all array ops use NumPy.

Taxonomy:
  ┌──────────────────────┬───────────────┬──────────────────────────┐
  │ Type                 │ Amb. interior │ Should be an error?      │
  ├──────────────────────┼───────────────┼──────────────────────────┤
  │ Bow-tie              │ Yes           │ Yes  → ERROR             │
  │ Figure Eight         │ Yes           │ Yes  → ERROR             │
  │ Crossing             │ Yes           │ Yes  → ERROR             │
  │ Pinch                │ No            │ Not necessarily → WARNING│
  │ Kiss                 │ No            │ Not necessarily → WARNING│
  │ Tangential touch     │ No            │ Not necessarily → WARNING│
  │ Spike                │ No            │ Generally no    → WARNING│
  │ Zero-area loop       │ No            │ Depends         → WARNING│
  │ Duplicate edge       │ Depends       │ Depends         → WARNING│
  └──────────────────────┴───────────────┴──────────────────────────┘
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

class RingSIType(Enum):
    BOW_TIE          = "Bow-tie"
    FIGURE_EIGHT     = "Figure Eight"
    CROSSING         = "Crossing"
    PINCH            = "Pinch"
    KISS             = "Kiss"
    TANGENTIAL_TOUCH = "Tangential Touch"
    SPIKE            = "Spike"
    ZERO_AREA_LOOP   = "Zero-area Loop"
    DUPLICATE_EDGE   = "Duplicate Edge"
    UNKNOWN          = "Unknown"


ERROR_TYPES: frozenset[RingSIType] = frozenset({
    RingSIType.BOW_TIE,
    RingSIType.FIGURE_EIGHT,
    RingSIType.CROSSING,
})

WARNING_TYPES: frozenset[RingSIType] = frozenset({
    RingSIType.PINCH,
    RingSIType.KISS,
    RingSIType.TANGENTIAL_TOUCH,
    RingSIType.SPIKE,
    RingSIType.ZERO_AREA_LOOP,
    RingSIType.DUPLICATE_EDGE,
    RingSIType.UNKNOWN,
})


@dataclass
class RingSIResult:
    si_type:     RingSIType
    is_error:    bool
    description: str
    touch_point: Optional[tuple[float, float]] = field(default=None)
    area_ratio:  Optional[float]               = field(default=None)

    @property
    def severity(self) -> str:
        return "ERROR" if self.is_error else "WARNING"


# ---------------------------------------------------------------------------
# Cheap coordinate checks (NumPy — no Shapely calls)
# ---------------------------------------------------------------------------

def _touch_point_from_reason(reason: str) -> Optional[tuple[float, float]]:
    """Extract (x, y) from a GEOS is_valid_reason string."""
    try:
        for marker in ("at or near point ", "at point ", "near point "):
            if marker in reason:
                parts = reason.split(marker, 1)[1].strip().split()
                if len(parts) >= 2:
                    return float(parts[0]), float(parts[1])
    except (ValueError, IndexError):
        pass
    return None


def _exterior_coords_np(geom):
    """
    Returns the exterior ring coordinates of a Polygon/MultiPolygon as a
    (N, 2) float64 NumPy array.  Returns None if geom has no exterior ring.
    """
    import numpy as np
    gtype = geom.geom_type
    if gtype == "Polygon":
        ring = geom.exterior
    elif gtype == "MultiPolygon":
        ring = max(geom.geoms, key=lambda g: g.area).exterior
    else:
        return None
    xy = np.asarray(ring.coords, dtype=np.float64)  # (N, 2) or (N, 3)
    return xy[:, :2]  # drop Z if present


def _check_kiss_fast(xy: "np.ndarray") -> bool:
    """
    Vectorised: returns True if any two consecutive rows are identical
    or within COORD_TOL of each other (Kiss / near-duplicate vertex).
    Uses NumPy diff — zero Python loops.
    """
    import numpy as np
    diff = xy[:-1] - xy[1:]                    # (N-1, 2)
    dist2 = (diff * diff).sum(axis=1)           # (N-1,)
    return bool((dist2 < _COORD_TOL_SQ).any())


def _check_spike_fast(xy: "np.ndarray", cos_thresh: float) -> bool:
    """
    Vectorised spike check: returns True if any interior angle has
    cos(angle) < cos_thresh  (i.e. angle > threshold).
    Uses NumPy cross-product normalisation — zero Python loops.
    """
    import numpy as np
    n = len(xy) - 1          # closed ring: last == first
    if n < 3:
        return False
    # Vectors: prev→curr and curr→next (rolled)
    v1 = xy[:-1] - np.roll(xy[:-1], 1, axis=0)   # p[i] - p[i-1]
    v2 = np.roll(xy[:-1], -1, axis=0) - xy[:-1]  # p[i+1] - p[i]
    len1 = np.sqrt((v1 * v1).sum(axis=1))
    len2 = np.sqrt((v2 * v2).sum(axis=1))
    mask = (len1 > 1e-15) & (len2 > 1e-15)
    dot  = (v1 * v2).sum(axis=1)
    cos_a = np.where(mask, dot / (len1 * len2), 0.0)
    cos_a = np.clip(cos_a, -1.0, 1.0)
    # Spike: cos_a < cos_thresh means angle > spike_angle_thresh
    return bool((cos_a < cos_thresh).any())


# Module-level constants (computed once)
_COORD_TOL     = 1e-8            # degrees — ~1 mm at equator
_COORD_TOL_SQ  = _COORD_TOL ** 2
_SPIKE_THRESH  = 0.5             # degrees
import math as _math
_SPIKE_COS     = _math.cos(_math.radians(180.0 - _SPIKE_THRESH))
_AREA_RATIO_THRESH = 0.999


# ---------------------------------------------------------------------------
# Core classifier
# ---------------------------------------------------------------------------

class RingSelfIntersectionClassifier:
    """
    Classifies Ring Self-Intersection errors by semantic subtype.

    Performance contract
    --------------------
    * Cheap checks (Kiss, Spike) use NumPy only — no Shapely call.
    * make_valid is called only if cheap checks do not fire.
    * classify_batch() vectorises make_valid + area over all suspects,
      avoiding N individual Shapely calls.

    Usage
    -----
    Single geometry::

        clf = RingSelfIntersectionClassifier()
        res = clf.classify(geom, reason="Ring Self-intersection at ...")

    Batch (preferred for performance)::

        results = clf.classify_batch(geom_list, reason_list)
    """

    def classify(self, geom, reason: str = "") -> RingSIResult:
        """Classify a single geometry. Prefer classify_batch for many geometries."""
        touch = _touch_point_from_reason(reason)
        try:
            return self._classify_one(geom, touch, fixed=None,
                                      orig_area=None, fixed_area=None)
        except Exception as exc:
            return RingSIResult(
                si_type=RingSIType.UNKNOWN,
                is_error=False,
                description=f"Classification error: {exc}",
                touch_point=touch,
            )

    def classify_batch(
        self,
        geoms: list,
        reasons: list[str],
    ) -> list[RingSIResult]:
        """
        Classify a list of Ring-SI suspect geometries.

        Vectorises make_valid and area computation over all suspects,
        then dispatches each to the cheap-first decision tree.
        """
        if not geoms:
            return []

        import numpy as np
        import shapely

        HAS_MV     = hasattr(shapely, "make_valid")
        HAS_AREA   = hasattr(shapely, "area")

        geom_arr = np.asarray(geoms, dtype=object)

        # ── Vectorised make_valid + area (one call each for all suspects) ──
        if HAS_MV:
            fixed_arr = shapely.make_valid(geom_arr)   # vectorised
        else:
            fixed_arr = geom_arr

        if HAS_AREA:
            orig_areas  = shapely.area(geom_arr)       # vectorised
            fixed_areas = shapely.area(fixed_arr)      # vectorised
        else:
            orig_areas  = np.array([g.area for g in geom_arr])
            fixed_areas = np.array([g.area for g in fixed_arr])

        results: list[RingSIResult] = []
        for geom, fixed, orig_a, fixed_a, reason in zip(
            geom_arr, fixed_arr, orig_areas, fixed_areas, reasons
        ):
            touch = _touch_point_from_reason(reason)
            try:
                res = self._classify_one(
                    geom, touch,
                    fixed=fixed,
                    orig_area=float(orig_a),
                    fixed_area=float(fixed_a),
                )
            except Exception as exc:
                res = RingSIResult(
                    si_type=RingSIType.UNKNOWN,
                    is_error=False,
                    description=f"Classification error: {exc}",
                    touch_point=touch,
                )
            results.append(res)
        return results

    # ------------------------------------------------------------------
    # Decision tree (called per-geometry with pre-computed values)
    # ------------------------------------------------------------------

    def _classify_one(
        self,
        geom,
        touch_point,
        fixed,           # pre-computed make_valid result (or None)
        orig_area,       # float or None
        fixed_area,      # float or None
    ) -> RingSIResult:

        import shapely

        # ── 1. Cheap: coordinate inspection (NumPy, no Shapely) ──────────
        xy = _exterior_coords_np(geom)
        if xy is not None and len(xy) >= 2:

            # Kiss / near-duplicate vertex
            if _check_kiss_fast(xy):
                return RingSIResult(
                    si_type=RingSIType.KISS,
                    is_error=False,
                    description=(
                        "Near-duplicate consecutive vertex (Kiss). "
                        "Floating-point precision artefact — no ambiguous interior."
                    ),
                    touch_point=touch_point,
                )

            # Spike
            if _check_spike_fast(xy, _SPIKE_COS):
                return RingSIResult(
                    si_type=RingSIType.SPIKE,
                    is_error=False,
                    description=(
                        "Spike vertex (interior angle ≈ 180°). "
                        "Ring goes out and returns — generally not a real error."
                    ),
                    touch_point=touch_point,
                )

        # ── 2. make_valid result (pre-computed in classify_batch) ─────────
        if fixed is None:
            # Called from classify() (single mode): compute now
            if hasattr(shapely, "make_valid"):
                fixed = shapely.make_valid(geom)
            else:
                fixed = geom

        if orig_area is None:
            orig_area  = geom.area  if hasattr(geom,  "area") else 0.0
        if fixed_area is None:
            fixed_area = fixed.area if hasattr(fixed, "area") else 0.0

        area_ratio = fixed_area / orig_area if orig_area > 1e-20 else None
        fixed_type = fixed.geom_type if fixed is not None else "Unknown"

        # ── 3. make_valid → MultiPolygon ──────────────────────────────────
        if "Multi" in fixed_type:
            n_parts = len(fixed.geoms) if hasattr(fixed, "geoms") else 1
            if area_ratio is not None and area_ratio < _AREA_RATIO_THRESH:
                si_type = RingSIType.BOW_TIE if n_parts == 2 else RingSIType.FIGURE_EIGHT
                return RingSIResult(
                    si_type=si_type,
                    is_error=True,
                    description=(
                        f"Ring crosses itself into {n_parts} separate area(s) "
                        f"(area ratio: {area_ratio:.4f}). "
                        "Ambiguous interior — genuine topological error."
                    ),
                    touch_point=touch_point,
                    area_ratio=area_ratio,
                )
            # Area preserved despite MultiPolygon → Pinch
            return RingSIResult(
                si_type=RingSIType.PINCH,
                is_error=False,
                description=(
                    "Ring self-touches at a single point (Pinch). "
                    "Area preserved — no ambiguous interior."
                ),
                touch_point=touch_point,
                area_ratio=area_ratio,
            )

        # ── 4. make_valid → area changed significantly (still Polygon) ────
        if area_ratio is not None and area_ratio < _AREA_RATIO_THRESH:
            return RingSIResult(
                si_type=RingSIType.CROSSING,
                is_error=True,
                description=(
                    f"Ring crosses itself with significant area change "
                    f"(ratio: {area_ratio:.4f}). "
                    "Ambiguous interior — genuine topological error."
                ),
                touch_point=touch_point,
                area_ratio=area_ratio,
            )

        # ── 5. make_valid produced no structural change ────────────────────
        if hasattr(shapely, "equals_exact"):
            unchanged = shapely.equals_exact(geom, fixed, tolerance=_COORD_TOL)
        else:
            unchanged = (geom.wkt == fixed.wkt)

        if unchanged:
            return RingSIResult(
                si_type=RingSIType.TANGENTIAL_TOUCH,
                is_error=False,
                description=(
                    "Tangentially touching / collinear segments. "
                    "make_valid produced no structural change — precision artefact."
                ),
                touch_point=touch_point,
                area_ratio=area_ratio,
            )

        # ── 6. Zero-area loop ──────────────────────────────────────────────
        if area_ratio is not None and abs(orig_area - fixed_area) < 1e-14:
            return RingSIResult(
                si_type=RingSIType.ZERO_AREA_LOOP,
                is_error=False,
                description="Zero-area loop — degenerate sub-ring with zero enclosed area.",
                touch_point=touch_point,
                area_ratio=area_ratio,
            )

        # ── 7. Fallback: duplicate edge ────────────────────────────────────
        return RingSIResult(
            si_type=RingSIType.DUPLICATE_EDGE,
            is_error=False,
            description=(
                "Possible duplicate edge — two segments share the same path. "
                "Context-dependent: review manually."
            ),
            touch_point=touch_point,
            area_ratio=area_ratio,
        )
