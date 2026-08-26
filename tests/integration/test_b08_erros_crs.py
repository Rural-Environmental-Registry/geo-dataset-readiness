# -*- coding: utf-8 -*-
"""
Integration tests — B08: CRS errors and warnings.
TC-21: HIDROGRAFIA EPSG:4326 → WARNING (accepted)
TC-22: APP EPSG:3857 → WARNING (accepted)
TC-23: VEGETACAO_ATUAL EPSG:31983 → NON_CONFORMANT (not accepted)
TC-24: VEGETACAO_2008 without CRS → NON_CONFORMANT
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
    return validate_dataset(base("B08_erros_crs.gpkg"))


@pytest.mark.integration
def test_b08_not_passed(report):
    assert not report.passed


@pytest.mark.integration
def test_b08_hidrografia_epsg4326_warning(report):
    """TC-21: EPSG:4326 is accepted but not preferred → WARNING."""
    checks = [
        c for c in report.conceptual_checks
        if c.name == "CRS" and c.layer == "HIDROGRAFIA"
    ]
    assert checks, "Expected CRS check for HIDROGRAFIA"
    assert checks[0].status == Status.WARNING
    assert "4326" in checks[0].details


@pytest.mark.integration
def test_b08_app_epsg3857_warning(report):
    """TC-22: EPSG:3857 is accepted but not preferred → WARNING."""
    checks = [
        c for c in report.conceptual_checks
        if c.name == "CRS" and c.layer == "APP"
    ]
    assert checks, "Expected CRS check for APP"
    assert checks[0].status == Status.WARNING
    assert "3857" in checks[0].details


@pytest.mark.integration
def test_b08_vegetacao_atual_non_standard_crs_error(report):
    """TC-23: EPSG:31983 is not in accepted list → NON_CONFORMANT."""
    checks = [
        c for c in report.conceptual_checks
        if c.name == "CRS" and c.layer == "VEGETACAO_ATUAL"
    ]
    assert checks, "Expected CRS check for VEGETACAO_ATUAL"
    assert checks[0].status == Status.NON_CONFORMANT


@pytest.mark.integration
def test_b08_warning_message_contains_expected_crs(report):
    """Warning details must mention the expected CRS (EPSG:4674)."""
    warnings = [
        c for c in report.conceptual_checks
        if c.name == "CRS" and c.status == Status.WARNING
    ]
    for w in warnings:
        assert "4674" in w.details, f"Expected EPSG:4674 in warning detail: {w.details}"
