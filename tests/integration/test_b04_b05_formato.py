# -*- coding: utf-8 -*-
"""
Integration tests — B04, B05: format consistency errors.
B04: corrupted .gpkg (text file with .gpkg extension).
B05: empty .gpkg (valid SQLite but no layers).
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
def test_b04_corrupted_not_conformant(base):
    report = validate_dataset(base("B04_corrompido.gpkg"))
    assert not report.passed


@pytest.mark.integration
def test_b04_readability_check_fails(base):
    report = validate_dataset(base("B04_corrompido.gpkg"))
    readability = [c for c in report.format_checks if c.name == "Dataset readability"]
    assert readability, "Expected a 'Dataset readability' check"
    assert readability[0].status == Status.NON_CONFORMANT


@pytest.mark.integration
def test_b04_error_message_is_user_friendly(base):
    """Raw GDAL messages must be replaced with user-friendly text."""
    report = validate_dataset(base("B04_corrompido.gpkg"))
    readability = [c for c in report.format_checks if c.name == "Dataset readability"]
    detail = readability[0].details
    # Must NOT contain raw GDAL technical phrases
    assert "not recognized as being in a supported file format" not in detail
    assert "not recognized as a supported file format" not in detail


@pytest.mark.integration
def test_b05_empty_not_conformant(base):
    """Empty GeoPackage (0 layers) must be NON_CONFORMANT."""
    report = validate_dataset(base("B05_vazio.gpkg"))
    assert not report.passed


@pytest.mark.integration
def test_b05_readability_check_zero_layers(base):
    report = validate_dataset(base("B05_vazio.gpkg"))
    readability = [c for c in report.format_checks if c.name == "Dataset readability"]
    assert readability
    assert readability[0].status == Status.NON_CONFORMANT
    # Detail must mention no layers, not a raw GDAL error
    assert "no layers" in readability[0].details.lower() or \
           "sem camadas" in readability[0].details.lower() or \
           "contains no layers" in readability[0].details.lower()
