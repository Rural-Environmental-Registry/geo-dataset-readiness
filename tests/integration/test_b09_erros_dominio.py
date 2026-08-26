# -*- coding: utf-8 -*-
"""
Integration tests — B09: domain consistency errors.
TC-26: HIDROGRAFIA CLASSE=9 out of [1,8] → NON_CONFORMANT
TC-27: APP CLASSE with NULL values → NON_CONFORMANT
TC-28: SERVIDAO CLASSE text non-numeric ("A","B","C") → NON_CONFORMANT
TC-29: RELEVO CLASSE text convertible ("1","2","3") → WARNING (not error)
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
    return validate_dataset(base("B09_erros_dominio.gpkg"))


@pytest.mark.integration
def test_b09_not_passed(report):
    assert not report.passed


@pytest.mark.integration
def test_b09_hidrografia_out_of_domain(report):
    """TC-26: value 9 outside [1,8] must produce NON_CONFORMANT domain check."""
    checks = [
        c for c in report.domain_checks
        if c.name == "CLASSE domain" and c.layer == "HIDROGRAFIA"
    ]
    assert checks, "Expected CLASSE domain check for HIDROGRAFIA"
    assert checks[0].status == Status.NON_CONFORMANT
    assert "9" in checks[0].details or "outside" in checks[0].details.lower()


@pytest.mark.integration
def test_b09_app_null_values(report):
    """TC-27: NULL values in APP CLASSE must produce NON_CONFORMANT."""
    checks = [
        c for c in report.domain_checks
        if c.name == "CLASSE null values" and c.layer == "APP"
    ]
    assert checks, "Expected CLASSE null values check for APP"
    assert checks[0].status == Status.NON_CONFORMANT


@pytest.mark.integration
def test_b09_servidao_non_numeric_classe_error(report):
    """TC-28: Non-numeric CLASSE ("A","B","C") → NON_CONFORMANT."""
    checks = [
        c for c in report.domain_checks
        if c.name == "CLASSE numeric type" and c.layer == "SERVIDAO"
    ]
    assert checks, "Expected CLASSE numeric type check for SERVIDAO"
    assert checks[0].status == Status.NON_CONFORMANT


@pytest.mark.integration
def test_b09_relevo_convertible_classe_warning(report):
    """TC-29: CLASSE dtype=object but values convertible → WARNING, not error."""
    checks = [
        c for c in report.domain_checks
        if c.name == "CLASSE numeric type" and c.layer == "RELEVO"
    ]
    assert checks, "Expected CLASSE numeric type check for RELEVO"
    assert checks[0].status == Status.WARNING, (
        f"Expected WARNING for convertible numeric CLASSE, got {checks[0].status}. "
        f"Detail: {checks[0].details}"
    )
