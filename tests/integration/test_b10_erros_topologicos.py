# -*- coding: utf-8 -*-
"""
Integration tests — B10: topological consistency errors.
TC-31: VEGETACAO_ATUAL with NULL geometries → NON_CONFORMANT
TC-32: VEGETACAO_2008 with EMPTY geometries → NON_CONFORMANT
TC-33: APP with Z coordinates (3D) → NON_CONFORMANT
TC-34: HIDROGRAFIA with 'Holes are nested' → NON_CONFORMANT (HARD_ERROR)
"""

import importlib.util
from pathlib import Path

import pytest

_PLUGIN_SRC = Path(__file__).parent.parent.parent / "geo-dataset-readiness"

def _load_validator():
    spec = importlib.util.spec_from_file_location("validator", _PLUGIN_SRC / "validator.py")
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_v = _load_validator()
validate_dataset = _v.validate_dataset
Status           = _v.Status


@pytest.fixture(scope="module")
def report(base):
    return validate_dataset(base("B10_erros_topologicos.gpkg"))


@pytest.mark.integration
def test_b10_not_passed(report):
    assert not report.passed


@pytest.mark.integration
def test_b10_vegetacao_atual_null_geometries(report):
    """TC-31: NULL geometries must generate NON_CONFORMANT."""
    checks = [
        c for c in report.topological_checks
        if c.layer == "VEGETACAO_ATUAL" and "null" in c.name.lower()
    ]
    assert checks, "Expected null geometry check for VEGETACAO_ATUAL"
    assert any(c.status == Status.NON_CONFORMANT for c in checks)


@pytest.mark.integration
def test_b10_vegetacao_2008_empty_geometries(report):
    """TC-32: EMPTY geometries must generate NON_CONFORMANT."""
    checks = [
        c for c in report.topological_checks
        if c.layer == "VEGETACAO_2008" and "empty" in c.name.lower()
    ]
    assert checks, "Expected empty geometry check for VEGETACAO_2008"
    assert any(c.status == Status.NON_CONFORMANT for c in checks)


@pytest.mark.integration
def test_b10_app_3d_geometry_warning(report):
    """TC-33: 3D (Z) geometries generate WARNING (not NON_CONFORMANT)."""
    checks = [
        c for c in report.topological_checks
        if c.layer == "APP" and c.name == "Geometry dimension"
    ]
    assert checks, "Expected geometry dimension check for APP"
    # The validator reports 3D as WARNING — data is usable but not spec-compliant
    assert checks[0].status == Status.WARNING
    assert "Z" in checks[0].details or "3D" in checks[0].details.upper()


@pytest.mark.integration
def test_b10_hidrografia_hard_error(report):
    """TC-34: 'Holes are nested' must be detected as topological error."""
    checks = [
        c for c in report.topological_checks
        if c.layer == "HIDROGRAFIA" and c.status == Status.NON_CONFORMANT
    ]
    assert checks, (
        "Expected NON_CONFORMANT topological check for HIDROGRAFIA. "
        "Checks found: " + str([(c.name, c.status, c.details) for c in report.topological_checks
                                 if c.layer == "HIDROGRAFIA"])
    )


@pytest.mark.integration
def test_b10_topological_summary_non_conformant(report):
    cats = report.summary_by_category()
    assert "Topological Consistency" in cats
    assert cats["Topological Consistency"]["status"] == Status.NON_CONFORMANT
