# -*- coding: utf-8 -*-
"""
Unit tests for ValidationReport.summary() and summary_by_category().
All inputs are synthetic — no file I/O.
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
Status           = _v.Status
CheckResult      = _v.CheckResult
ValidationReport = _v.ValidationReport


def _report(*checks) -> ValidationReport:
    r = ValidationReport(file_path="dummy.gpkg")
    r.checks = list(checks)
    return r


def _check(name, status, category="format", layer=""):
    return CheckResult(name=name, status=status, category=category, layer=layer)


# ===========================================================================
# summary()
# ===========================================================================

class TestSummary:

    @pytest.mark.unit
    def test_all_conformant(self):
        r = _report(
            _check("A", Status.CONFORMANT),
            _check("B", Status.CONFORMANT),
        )
        s = r.summary()
        assert "2 rules executed" in s
        assert "2 conformant" in s
        assert "non-conformant" not in s

    @pytest.mark.unit
    def test_mixed_statuses(self):
        r = _report(
            _check("A", Status.CONFORMANT),
            _check("B", Status.NON_CONFORMANT),
            _check("C", Status.WARNING),
        )
        s = r.summary()
        assert "3 rules executed" in s
        assert "1 conformant" in s
        assert "1 non-conformant" in s
        assert "1 warning" in s

    @pytest.mark.unit
    def test_fid_detail_rows_excluded(self):
        r = _report(
            _check("Topological errors",      Status.NON_CONFORMANT, "topological"),
            _check("Error in feature FID 1",  Status.NON_CONFORMANT, "topological"),
            _check("Error in feature FID 2",  Status.NON_CONFORMANT, "topological"),
            _check("Warning in feature FID 3",Status.WARNING,        "topological"),
        )
        s = r.summary()
        # Only 1 rule-level entry; 3 FID detail rows must be excluded
        assert "1 rules executed" in s

    @pytest.mark.unit
    def test_empty_report(self):
        r = _report()
        s = r.summary()
        assert "0 rules executed" in s

    @pytest.mark.unit
    def test_only_warnings_no_nonconf_label(self):
        r = _report(
            _check("CRS", Status.WARNING, "conceptual"),
        )
        s = r.summary()
        assert "non-conformant" not in s
        assert "warning" in s


# ===========================================================================
# summary_by_category()
# ===========================================================================

class TestSummaryByCategory:

    @pytest.mark.unit
    def test_four_categories_populated(self):
        r = _report(
            _check("F",  Status.CONFORMANT, "format"),
            _check("C",  Status.CONFORMANT, "conceptual"),
            _check("D",  Status.CONFORMANT, "domain"),
            _check("T",  Status.CONFORMANT, "topological"),
        )
        cats = r.summary_by_category()
        assert "Format Consistency"      in cats
        assert "Conceptual Consistency"  in cats
        assert "Domain Consistency"      in cats
        assert "Topological Consistency" in cats

    @pytest.mark.unit
    def test_empty_category_not_included(self):
        r = _report(_check("F", Status.CONFORMANT, "format"))
        cats = r.summary_by_category()
        assert "Conceptual Consistency" not in cats

    @pytest.mark.unit
    def test_counts_correct(self):
        r = _report(
            _check("A", Status.CONFORMANT,     "domain"),
            _check("B", Status.NON_CONFORMANT, "domain"),
            _check("C", Status.WARNING,        "domain"),
        )
        d = r.summary_by_category()["Domain Consistency"]
        assert d["total"]         == 3
        assert d["conformant"]    == 1
        assert d["non_conformant"]== 1
        assert d["warnings"]      == 1

    @pytest.mark.unit
    def test_status_nonconf_takes_precedence_over_warning(self):
        r = _report(
            _check("A", Status.WARNING,        "conceptual"),
            _check("B", Status.NON_CONFORMANT, "conceptual"),
        )
        assert r.summary_by_category()["Conceptual Consistency"]["status"] == Status.NON_CONFORMANT

    @pytest.mark.unit
    def test_status_warning_when_no_error(self):
        r = _report(
            _check("A", Status.CONFORMANT, "conceptual"),
            _check("B", Status.WARNING,    "conceptual"),
        )
        assert r.summary_by_category()["Conceptual Consistency"]["status"] == Status.WARNING

    @pytest.mark.unit
    def test_fid_rows_excluded_from_topological_count(self):
        r = _report(
            _check("Topological errors",     Status.NON_CONFORMANT, "topological"),
            _check("Error in feature FID 1", Status.NON_CONFORMANT, "topological"),
            _check("Error in feature FID 2", Status.NON_CONFORMANT, "topological"),
        )
        t = r.summary_by_category()["Topological Consistency"]
        assert t["total"] == 1
        assert t["non_conformant"] == 1

    @pytest.mark.unit
    def test_category_only_fid_rows_skipped(self):
        """A category consisting only of FID detail rows should not appear."""
        r = _report(
            _check("Error in feature FID 1", Status.NON_CONFORMANT, "topological"),
            _check("Error in feature FID 2", Status.NON_CONFORMANT, "topological"),
        )
        cats = r.summary_by_category()
        assert "Topological Consistency" not in cats
