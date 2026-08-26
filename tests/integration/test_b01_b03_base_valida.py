# -*- coding: utf-8 -*-
"""
Integration tests — B01, B02, B03: valid bases (gpkg, gdb, zip).
Expected: all checks pass, no warnings on mandatory layers.
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


@pytest.mark.integration
def test_b01_gpkg_passes(base):
    report = validate_dataset(base("B01_base_valida.gpkg"))
    assert report.passed, f"Expected pass. Summary: {report.summary()}"


@pytest.mark.integration
def test_b01_has_no_non_conformant(base):
    report = validate_dataset(base("B01_base_valida.gpkg"))
    non_conf = [c for c in report.checks if c.status == Status.NON_CONFORMANT]
    assert non_conf == [], f"Unexpected NON_CONFORMANT: {[(c.name, c.details) for c in non_conf]}"


@pytest.mark.integration
def test_b01_four_categories_present(base):
    report = validate_dataset(base("B01_base_valida.gpkg"))
    cats = report.summary_by_category()
    assert "Format Consistency"      in cats
    assert "Conceptual Consistency"  in cats
    assert "Domain Consistency"      in cats
    assert "Topological Consistency" in cats


@pytest.mark.integration
def test_b02_gdb_passes(base):
    report = validate_dataset(base("B02_base_valida.gdb"))
    assert report.passed, f"Expected pass. Summary: {report.summary()}"


@pytest.mark.integration
def test_b03_zip_passes(base):
    report = validate_dataset(base("B03_base_valida_zipada.zip"))
    assert report.passed, f"Expected pass. Summary: {report.summary()}"
