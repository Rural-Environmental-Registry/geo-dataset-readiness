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
plugin.py - QGIS Integration

Registers the plugin in the menu, creates the toolbar action and opens the validation dialog.
"""

import os

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .dialog import ValidationDialog


class GeoDatasetReadinessPlugin:
    """QGIS Plugin - SICAR AD: Validate Environmental Dataset Structure."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None
        self.dialog = None

    def initGui(self):
        """Initializes the plugin interface (called by QGIS)."""
        icon_path = os.path.join(self.plugin_dir, "icon.ico")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        self.action = QAction(
            icon, "Validate Environmental Dataset Structure", self.iface.mainWindow()
        )
        self.action.setObjectName("sicarAdValidateDatasetStructureAction")
        self.action.setWhatsThis(
            "Logical consistency validation of the environmental dataset according to ISO 19157:2013"
        )
        self.action.setStatusTip("Opens the environmental dataset structure validator")
        self.action.triggered.connect(self.run)

        # Add to menu and toolbar
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&SICAR AD", self.action)

    def unload(self):
        """Removes the plugin from the interface (called by QGIS)."""
        self.iface.removePluginMenu("&SICAR AD", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        """Opens the validation dialog."""
        self.dialog = ValidationDialog(self.iface.mainWindow())
        self.dialog.show()
