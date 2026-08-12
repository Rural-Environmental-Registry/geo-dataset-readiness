# -*- coding: utf-8 -*-
# Copyright (C) 2026 Dataprev
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
QGIS Plugin - Validate Environmental Dataset Structure
"""

# ---------------------------------------------------------------------------
# Dependency check — must run BEFORE any import of scientific libraries.
# Uses importlib.util.find_spec() which only probes the module path without
# actually importing, so it is safe and fast on all platforms.
# ---------------------------------------------------------------------------

import importlib.util
import sys
import platform

_REQUIRED = {
    "geopandas": "geopandas",
    "pyogrio":   "pyogrio",
    "shapely":   "shapely",
}

def _check_dependencies() -> list[str]:
    """Returns list of missing package names (empty = all present)."""
    return [pkg for pkg in _REQUIRED if importlib.util.find_spec(pkg) is None]


def _install_hint() -> str:
    """Returns OS-appropriate installation instructions."""
    os_name = platform.system()
    if os_name == "Linux":
        return (
            "sudo pip3 install geopandas pyogrio shapely --break-system-packages\n\n"
            "Or, if your distribution provides the packages:\n"
            "sudo apt install python3-geopandas python3-shapely"
        )
    elif os_name == "Darwin":
        return "pip3 install geopandas pyogrio shapely"
    else:
        # Windows — QGIS ships with these libraries; if they are missing
        # the QGIS installation itself is likely incomplete.
        return (
            "Reinstall QGIS using the official OSGeo4W installer, which\n"
            "includes geopandas, pyogrio and shapely bundled with QGIS."
        )


def classFactory(iface):
    missing = _check_dependencies()

    if missing:
        # Show a user-friendly message box instead of a cryptic traceback.
        try:
            from qgis.PyQt.QtWidgets import QMessageBox
        except ImportError:
            # Absolute last resort — Qt itself is unavailable (should never happen).
            raise ImportError(
                f"geo-dataset-readiness: missing dependencies: {', '.join(missing)}"
            )

        pkgs   = ", ".join(missing)
        hint   = _install_hint()
        python = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        os_str = f"{platform.system()} {platform.release()}"

        msg = QMessageBox()
        msg.setWindowTitle("geo-dataset-readiness — Missing Dependencies")
        msg.setIcon(
            QMessageBox.Critical
            if hasattr(QMessageBox, "Critical")
            else QMessageBox.Icon.Critical
        )
        msg.setText(
            f"<b>The plugin could not be loaded because the following Python "
            f"libraries are missing:</b><br><br>"
            f"<tt style='color:#E52207;'>{pkgs}</tt>"
        )
        msg.setInformativeText(
            f"<b>How to install:</b><br><pre>{hint}</pre>"
            f"<br>After installing, restart QGIS.<br><br>"
            f"<small>Python {python} &nbsp;·&nbsp; {os_str}</small>"
        )
        msg.setStandardButtons(
            QMessageBox.Ok
            if hasattr(QMessageBox, "Ok")
            else QMessageBox.StandardButton.Ok
        )
        msg.exec_()

        # Return a no-op stub so QGIS does not crash after the dialog closes.
        class _StubPlugin:
            def __init__(self, iface): pass
            def initGui(self): pass
            def unload(self): pass

        return _StubPlugin(iface)

    # All dependencies present — load normally.
    from .plugin import GeoDatasetReadinessPlugin
    return GeoDatasetReadinessPlugin(iface)

