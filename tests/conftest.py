# -*- coding: utf-8 -*-
"""
conftest.py — Shared pytest fixtures for geo-dataset-readiness tests.

Fixtures available to all test modules:
  - BASE_DIR   : Path to tests/data/bases_teste/
  - base(name) : convenience function returning Path for a named base
"""

import sys
import os
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Make the plugin source importable without QGIS being installed.
# The validator module only needs geopandas / pyogrio / shapely.
# ---------------------------------------------------------------------------
REPO_ROOT   = Path(__file__).parent.parent
PLUGIN_SRC  = REPO_ROOT / "geo-dataset-readiness"
DATA_DIR    = REPO_ROOT / "tests" / "data" / "bases_teste"

if str(PLUGIN_SRC) not in sys.path:
    sys.path.insert(0, str(PLUGIN_SRC))

# Stub out the qgis namespace so validator.py can be imported without QGIS.
# validator.py itself does NOT import qgis — but other modules in the package
# (plugin.py, dialog.py) do. We only import validator directly, so this stub
# is here as a safety net for transitive imports.
import types

if "qgis" not in sys.modules:
    qgis_stub = types.ModuleType("qgis")
    qgis_stub.PyQt = types.ModuleType("qgis.PyQt")
    sys.modules.setdefault("qgis", qgis_stub)
    sys.modules.setdefault("qgis.PyQt", qgis_stub.PyQt)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def base_dir() -> Path:
    """Returns the path to the homologation test bases directory."""
    if not DATA_DIR.exists():
        pytest.skip(
            f"Test bases not found at {DATA_DIR}. "
            "Run tests/data/criar_bases_teste.py to generate them."
        )
    return DATA_DIR


@pytest.fixture(scope="session")
def base(base_dir):
    """
    Factory fixture: returns a function that resolves a base filename to a Path.

    Usage:
        def test_something(base):
            path = base("B01_base_valida.gpkg")
    """
    def _resolve(filename: str) -> Path:
        p = base_dir / filename
        if not p.exists():
            pytest.skip(f"Base not found: {p}")
        return p
    return _resolve


@pytest.fixture(scope="session")
def validator():
    """Imports and returns the validator module (session-scoped for speed)."""
    import importlib
    # Import directly from the source directory, bypassing the QGIS package
    # loader that would require qgis.PyQt etc.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "validator", PLUGIN_SRC / "validator.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
