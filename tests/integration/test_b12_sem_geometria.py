# -*- coding: utf-8 -*-
"""
Integration tests — B12: layer without geometry column.
TC-15: HIDROGRAFIA written as plain attribute table (no geometry column).
Expected: "Geometry column missing" NON_CONFORMANT, not a crash.
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
    return validate_dataset(base("B12_sem_geometria.gpkg"))


@pytest.mark.integration
def test_b12_not_passed(report):
    assert not report.passed


@pytest.mark.integration
def test_b12_geometry_column_missing_check(report):
    """TC-15: HIDROGRAFIA without geometry column must produce the specific check."""
    checks = [
        c for c in report.checks
        if c.name == "Geometry column missing" and c.layer == "HIDROGRAFIA"
    ]
    assert checks, (
        "Expected 'Geometry column missing' check for HIDROGRAFIA. "
        "All checks: " + str([(c.name, c.layer, c.status) for c in report.checks])
    )
    assert checks[0].status == Status.NON_CONFORMANT


@pytest.mark.integration
def test_b12_no_crash_on_geometry_less_layer(base):
    """Validating a layer without geometry must not raise an exception."""
    try:
        validate_dataset(base("B12_sem_geometria.gpkg"))
    except Exception as exc:
        pytest.fail(f"validate_dataset raised an unexpected exception: {exc}")


@pytest.mark.integration
def test_b12_other_layers_still_validated(report):
    """Other layers (with geometry) must still produce checks."""
    layers_checked = {c.layer for c in report.conceptual_checks if c.layer}
    # At least some of the non-HIDROGRAFIA layers should appear
    other_layers = layers_checked - {"HIDROGRAFIA", "(all)", ""}
    assert other_layers, "Expected other layers to be validated besides HIDROGRAFIA"
