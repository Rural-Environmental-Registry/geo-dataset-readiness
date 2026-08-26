# -*- coding: utf-8 -*-
"""
Unit tests for pure utility functions in validator.py.
No file I/O — all inputs are synthetic.
"""

import sys
import types
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import validator directly (no QGIS required)
# ---------------------------------------------------------------------------
import importlib.util

_PLUGIN_SRC = Path(__file__).parent.parent.parent / "geo-dataset-readiness"

def _load_validator():
    spec = importlib.util.spec_from_file_location("validator", _PLUGIN_SRC / "validator.py")
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_v = _load_validator()

find_layer_name = _v.find_layer_name
detect_format   = _v.detect_format
Status          = _v.Status
CheckResult     = _v.CheckResult
ValidationReport = _v.ValidationReport
EXPECTED_LAYERS  = _v.EXPECTED_LAYERS


# ===========================================================================
# find_layer_name
# ===========================================================================

class TestFindLayerName:

    @pytest.mark.unit
    def test_exact_match(self):
        assert find_layer_name(["HIDROGRAFIA", "APP"], "HIDROGRAFIA") == "HIDROGRAFIA"

    @pytest.mark.unit
    def test_case_insensitive_lower_in_list(self):
        assert find_layer_name(["hidrografia", "app"], "HIDROGRAFIA") == "hidrografia"

    @pytest.mark.unit
    def test_case_insensitive_upper_query(self):
        assert find_layer_name(["Hidrografia"], "hidrografia") == "Hidrografia"

    @pytest.mark.unit
    def test_not_found_returns_none(self):
        assert find_layer_name(["APP", "RELEVO"], "INEXISTENTE") is None

    @pytest.mark.unit
    def test_empty_list_returns_none(self):
        assert find_layer_name([], "HIDROGRAFIA") is None

    @pytest.mark.unit
    def test_first_match_returned(self):
        # Should return the first matching name in insertion order
        result = find_layer_name(["app", "APP"], "APP")
        assert result == "app"


# ===========================================================================
# detect_format
# ===========================================================================

class TestDetectFormat:

    @pytest.mark.unit
    def test_gpkg_file(self, tmp_path):
        f = tmp_path / "base.gpkg"
        f.touch()
        valid, desc = detect_format(f)
        assert valid
        assert "GeoPackage" in desc

    @pytest.mark.unit
    def test_gdb_directory(self, tmp_path):
        d = tmp_path / "base.gdb"
        d.mkdir()
        valid, desc = detect_format(d)
        assert valid
        assert "GeoDatabase" in desc

    @pytest.mark.unit
    def test_zip_file(self, tmp_path):
        f = tmp_path / "base.gpkg.zip"
        f.touch()
        valid, desc = detect_format(f)
        assert valid

    @pytest.mark.unit
    def test_unsupported_extension(self, tmp_path):
        f = tmp_path / "base.shp"
        f.touch()
        valid, _ = detect_format(f)
        assert not valid

    @pytest.mark.unit
    def test_nonexistent_gpkg_extension_still_valid_format(self, tmp_path):
        # detect_format checks extension only, not file existence.
        # A path with .gpkg suffix is considered a valid format regardless.
        f = tmp_path / "nonexistent.gpkg"
        valid, desc = detect_format(f)
        # The format is recognized; existence is checked at a higher level
        assert valid
        assert "GeoPackage" in desc

    @pytest.mark.unit
    def test_extension_only_no_existence_check_for_zip(self, tmp_path):
        f = tmp_path / "base.zip"
        f.touch()
        valid, _ = detect_format(f)
        assert valid


# ===========================================================================
# Status enum
# ===========================================================================

class TestStatus:

    @pytest.mark.unit
    def test_values_are_distinct(self):
        assert Status.CONFORMANT != Status.NON_CONFORMANT
        assert Status.CONFORMANT != Status.WARNING
        assert Status.NON_CONFORMANT != Status.WARNING

    @pytest.mark.unit
    def test_string_values(self):
        assert Status.CONFORMANT.value == "CONFORMANT"
        assert Status.NON_CONFORMANT.value == "NON-CONFORMANT"
        assert Status.WARNING.value == "WARNING"


# ===========================================================================
# CheckResult dataclass
# ===========================================================================

class TestCheckResult:

    @pytest.mark.unit
    def test_default_fields(self):
        c = CheckResult(name="Test", status=Status.CONFORMANT)
        assert c.details == ""
        assert c.category == ""
        assert c.layer == ""
        assert c.wkt == ""

    @pytest.mark.unit
    def test_full_fields(self):
        c = CheckResult(
            name="CRS",
            status=Status.WARNING,
            details="EPSG:4326 accepted",
            category="conceptual",
            layer="HIDROGRAFIA",
        )
        assert c.name == "CRS"
        assert c.status == Status.WARNING
        assert c.layer == "HIDROGRAFIA"


# ===========================================================================
# ValidationReport
# ===========================================================================

class TestValidationReport:

    def _make_report(self, checks):
        r = ValidationReport(file_path="test.gpkg")
        r.checks = checks
        return r

    @pytest.mark.unit
    def test_passed_all_conformant(self):
        r = self._make_report([
            CheckResult("A", Status.CONFORMANT, category="format"),
            CheckResult("B", Status.CONFORMANT, category="conceptual"),
        ])
        assert r.passed

    @pytest.mark.unit
    def test_passed_false_when_non_conformant(self):
        r = self._make_report([
            CheckResult("A", Status.CONFORMANT, category="format"),
            CheckResult("B", Status.NON_CONFORMANT, category="conceptual"),
        ])
        assert not r.passed

    @pytest.mark.unit
    def test_passed_true_when_only_warnings(self):
        r = self._make_report([
            CheckResult("A", Status.CONFORMANT, category="format"),
            CheckResult("B", Status.WARNING, category="conceptual"),
        ])
        assert r.passed
        assert r.has_warnings

    @pytest.mark.unit
    def test_category_filters(self):
        checks = [
            CheckResult("F", Status.CONFORMANT, category="format"),
            CheckResult("C", Status.CONFORMANT, category="conceptual"),
            CheckResult("D", Status.CONFORMANT, category="domain"),
            CheckResult("T", Status.CONFORMANT, category="topological"),
        ]
        r = self._make_report(checks)
        assert len(r.format_checks) == 1
        assert len(r.conceptual_checks) == 1
        assert len(r.domain_checks) == 1
        assert len(r.topological_checks) == 1

    @pytest.mark.unit
    def test_summary_excludes_fid_detail_entries(self):
        """FID detail rows must NOT be counted as individual rules."""
        checks = [
            CheckResult("Topological errors", Status.NON_CONFORMANT, category="topological"),
            CheckResult("Error in feature FID 10", Status.NON_CONFORMANT, category="topological"),
            CheckResult("Error in feature FID 20", Status.NON_CONFORMANT, category="topological"),
            CheckResult("CRS", Status.CONFORMANT, category="conceptual"),
        ]
        r = self._make_report(checks)
        summary = r.summary()
        # Only 2 rule-level checks should be counted (not the 2 FID detail entries)
        assert "2 rules executed" in summary

    @pytest.mark.unit
    def test_summary_by_category_excludes_fid_entries(self):
        checks = [
            CheckResult("Topological errors", Status.NON_CONFORMANT, category="topological"),
            CheckResult("Error in feature FID 1", Status.NON_CONFORMANT, category="topological"),
            CheckResult("Error in feature FID 2", Status.NON_CONFORMANT, category="topological"),
        ]
        r = self._make_report(checks)
        cats = r.summary_by_category()
        assert "Topological Consistency" in cats
        # Only 1 rule (not 3)
        assert cats["Topological Consistency"]["total"] == 1

    @pytest.mark.unit
    def test_summary_by_category_status_precedence(self):
        """NON_CONFORMANT takes precedence over WARNING."""
        checks = [
            CheckResult("CRS", Status.WARNING, category="conceptual"),
            CheckResult("Layers", Status.NON_CONFORMANT, category="conceptual"),
        ]
        r = self._make_report(checks)
        cats = r.summary_by_category()
        assert cats["Conceptual Consistency"]["status"] == Status.NON_CONFORMANT

    @pytest.mark.unit
    def test_summary_by_category_warning_when_no_errors(self):
        checks = [
            CheckResult("CRS", Status.WARNING, category="conceptual"),
            CheckResult("Layers", Status.CONFORMANT, category="conceptual"),
        ]
        r = self._make_report(checks)
        cats = r.summary_by_category()
        assert cats["Conceptual Consistency"]["status"] == Status.WARNING


# ===========================================================================
# Expected layers list
# ===========================================================================

class TestExpectedLayers:

    @pytest.mark.unit
    def test_has_ten_layers(self):
        assert len(EXPECTED_LAYERS) == 10

    @pytest.mark.unit
    def test_contains_required_layers(self):
        required = {
            "HIDROGRAFIA", "APP", "VEGETACAO_ATUAL", "VEGETACAO_2008",
            "AREA_ANTROPIZADA", "AREA_CONSOLIDADA", "SERVIDAO",
            "RELEVO", "USO_RESTRITO", "APP_ESPECIAL",
        }
        assert required == set(EXPECTED_LAYERS)
