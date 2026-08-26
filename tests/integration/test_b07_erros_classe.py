# -*- coding: utf-8 -*-
"""
Integration tests — B07: CLASSE attribute errors.
TC-17: HIDROGRAFIA missing CLASSE → NON_CONFORMANT
TC-18: AREA_CONSOLIDADA has CLASSE (forbidden) → NON_CONFORMANT
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
    return validate_dataset(base("B07_erros_classe.gpkg"))


@pytest.mark.integration
def test_b07_not_passed(report):
    assert not report.passed


@pytest.mark.integration
def test_b07_hidrografia_missing_classe(report):
    """TC-17: HIDROGRAFIA without CLASSE must be NON_CONFORMANT."""
    checks = [
        c for c in report.conceptual_checks
        if c.name == "CLASSE attribute" and c.layer == "HIDROGRAFIA"
    ]
    assert checks, "Expected CLASSE attribute check for HIDROGRAFIA"
    assert checks[0].status == Status.NON_CONFORMANT


@pytest.mark.integration
def test_b07_area_consolidada_forbidden_classe(report):
    """TC-18: AREA_CONSOLIDADA with CLASSE must be NON_CONFORMANT."""
    checks = [
        c for c in report.conceptual_checks
        if c.name == "Absence of CLASSE" and c.layer == "AREA_CONSOLIDADA"
    ]
    assert checks, "Expected 'Absence of CLASSE' check for AREA_CONSOLIDADA"
    assert checks[0].status == Status.NON_CONFORMANT
