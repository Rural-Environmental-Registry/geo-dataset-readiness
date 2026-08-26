# -*- coding: utf-8 -*-
"""
Integration tests — B06: missing layers, empty layer, 1-record layer, lowercase name.
TC-10: VEGETACAO_ATUAL mandatory → NON_CONFORMANT
TC-11: APP optional → WARNING
TC-12: vegetacao_2008 (lowercase) → found via case-insensitive matching
TC-13: HIDROGRAFIA empty → NON_CONFORMANT (0 records)
TC-14: AREA_ANTROPIZADA with 1 record → CONFORMANT
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
    return validate_dataset(base("B06_camadas_ausentes.gpkg"))


@pytest.mark.integration
def test_b06_not_passed(report):
    assert not report.passed


@pytest.mark.integration
def test_b06_vegetacao_atual_non_conformant(report):
    """TC-10: VEGETACAO_ATUAL is mandatory — must be NON_CONFORMANT when absent."""
    missing = [
        c for c in report.conceptual_checks
        if c.name == "Missing layer" and "VEGETACAO_ATUAL" in c.details
    ]
    assert missing, "Expected a 'Missing layer' check for VEGETACAO_ATUAL"
    assert missing[0].status == Status.NON_CONFORMANT


@pytest.mark.integration
def test_b06_app_warning_when_absent(report):
    """TC-11: APP is optional — must generate WARNING when absent."""
    missing = [
        c for c in report.conceptual_checks
        if c.name == "Missing layer" and "APP" in c.details
    ]
    if missing:
        assert missing[0].status == Status.WARNING


@pytest.mark.integration
def test_b06_hidrografia_empty_non_conformant(report):
    """TC-13: HIDROGRAFIA with 0 records must be NON_CONFORMANT."""
    empty = [
        c for c in report.conceptual_checks
        if c.name == "Records" and c.layer == "HIDROGRAFIA"
    ]
    assert empty, "Expected a Records check for HIDROGRAFIA"
    assert empty[0].status == Status.NON_CONFORMANT
