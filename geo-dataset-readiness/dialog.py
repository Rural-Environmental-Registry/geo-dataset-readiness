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
dialog.py - SICAR AD - Validate Environmental Dataset Structure

Graphical interface redesigned according to the Digital Government Standard (GOV.BR DS).
Visual reference: https://www.gov.br/ds/home
"""

from pathlib import Path

from qgis.PyQt.QtCore import Qt, QCoreApplication
from qgis.PyQt.QtGui import QColor, QIntValidator
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QLineEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QMessageBox,
    QProgressBar,
    QSizePolicy,
    QTabWidget,
    QWidget,
    QTextEdit,
    QFrame,
    QCheckBox,
    QComboBox,
    QTextBrowser,
)

from .validator import (
    validate_dataset,
    Status,
    ValidationReport,
    CheckResult,
    EXPECTED_LAYERS,
    export_report_pdf,
)

# ---------------------------------------------------------------------------
# Application configuration (plugin-config.json)
# ---------------------------------------------------------------------------

import json as _json
import os as _os


def _load_plugin_config() -> dict:
    """Loads application configuration from plugin-config.json."""
    config_path = _os.path.join(_os.path.dirname(__file__), "plugin-config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return _json.load(f)
    except (FileNotFoundError, _json.JSONDecodeError):
        return {}


_PLUGIN_CONFIG = _load_plugin_config()
REFERENCES = _PLUGIN_CONFIG.get("references", [])

# Qt5 (QGIS 3.x) / Qt6 (QGIS 4.x) compatibility
try:
    _SP_EXPANDING = QSizePolicy.Policy.Expanding
except AttributeError:
    _SP_EXPANDING = QSizePolicy.Expanding

try:
    _CURSOR_POINTING = Qt.CursorShape.PointingHandCursor
except AttributeError:
    _CURSOR_POINTING = Qt.PointingHandCursor

try:
    _ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
except AttributeError:
    _ALIGN_CENTER = Qt.AlignCenter

try:
    _SHOW_DIRS_ONLY = QFileDialog.Option.ShowDirsOnly
except AttributeError:
    _SHOW_DIRS_ONLY = QFileDialog.ShowDirsOnly

try:
    _QT_CHECKED = Qt.CheckState.Checked
except AttributeError:
    _QT_CHECKED = Qt.Checked


# ---------------------------------------------------------------------------
# Design Tokens — Digital Government Standard (GOV.BR DS)
# ---------------------------------------------------------------------------

class GovBRTokens:
    """Design tokens based on the Digital Government Standard."""
    SURFACE_LIGHT = "#FFFFFF"
    SURFACE_ALT = "#F8F8F8"
    SURFACE_DARK = "#071D41"
    TEXT_PRIMARY = "#333333"
    TEXT_SECONDARY = "#636363"
    TEXT_ON_DARK = "#FFFFFF"
    INTERACTIVE = "#1351B4"
    INTERACTIVE_HOVER = "#0C326F"
    INTERACTIVE_LIGHT = "#D4E5FF"
    SUCCESS = "#168821"
    SUCCESS_BG = "#E3F5E1"
    ERROR = "#E52207"
    ERROR_BG = "#FDE0DB"
    WARNING = "#FFCD07"
    WARNING_TEXT = "#D2600F"
    WARNING_BG = "#FFF5C2"
    INFO = "#155BCB"
    INFO_BG = "#D4E5FF"
    BORDER = "#CCCCCC"
    BORDER_LIGHT = "#E6E6E6"
    DIVIDER = "#E6E6E6"
    SPACE_XS = 4
    SPACE_SM = 8
    SPACE_MD = 16
    SPACE_LG = 24
    RADIUS_SM = 4
    RADIUS_MD = 8
    FONT_FAMILY = "Rawline, Roboto, 'Segoe UI', sans-serif"
    FONT_SIZE_XS = 11
    FONT_SIZE_SM = 12
    FONT_SIZE_MD = 14
    FONT_SIZE_LG = 16
    FONT_SIZE_XL = 20


def _govbr_stylesheet() -> str:
    """Returns the Qt stylesheet inspired by the Digital Government Standard."""
    T = GovBRTokens
    return f"""
    QDialog {{
        background-color: {T.SURFACE_LIGHT};
        color: {T.TEXT_PRIMARY};
        font-family: {T.FONT_FAMILY};
        font-size: {T.FONT_SIZE_MD}px;
    }}
    QLabel {{
        color: {T.TEXT_PRIMARY};
        font-family: {T.FONT_FAMILY};
    }}
    QLabel#headerTitle {{
        color: {T.TEXT_ON_DARK};
        font-size: {T.FONT_SIZE_XL}px;
        font-weight: 600;
    }}
    QLabel#headerSubtitle {{
        color: rgba(255, 255, 255, 0.8);
        font-size: {T.FONT_SIZE_XS}px;
    }}
    QLabel#progressLabel {{
        color: {T.TEXT_SECONDARY};
        font-size: {T.FONT_SIZE_SM}px;
    }}
    QPushButton {{
        font-family: {T.FONT_FAMILY};
        font-size: {T.FONT_SIZE_MD}px;
        font-weight: 600;
        border: none;
        border-radius: {T.RADIUS_SM}px;
        padding: {T.SPACE_SM}px {T.SPACE_LG}px;
        min-height: 36px;
    }}
    QPushButton#primaryBtn {{
        background-color: {T.INTERACTIVE};
        color: {T.TEXT_ON_DARK};
    }}
    QPushButton#primaryBtn:hover {{
        background-color: {T.INTERACTIVE_HOVER};
    }}
    QPushButton#primaryBtn:disabled {{
        background-color: {T.BORDER};
        color: {T.TEXT_SECONDARY};
    }}
    QPushButton#secondaryBtn {{
        background-color: transparent;
        color: {T.INTERACTIVE};
        border: 1px solid {T.INTERACTIVE};
    }}
    QPushButton#secondaryBtn:hover {{
        background-color: {T.INTERACTIVE_LIGHT};
    }}
    QPushButton#secondaryBtn:disabled {{
        background-color: {T.BORDER_LIGHT};
        color: {T.TEXT_SECONDARY};
        border: 1px solid {T.BORDER};
    }}
    QPushButton#tertiaryBtn {{
        background-color: transparent;
        color: {T.INTERACTIVE};
        border: none;
    }}
    QPushButton#tertiaryBtn:hover {{
        background-color: {T.INTERACTIVE_LIGHT};
    }}
    QLineEdit {{
        font-family: {T.FONT_FAMILY};
        font-size: {T.FONT_SIZE_MD}px;
        color: {T.TEXT_PRIMARY};
        background-color: {T.SURFACE_LIGHT};
        border: 1px solid {T.BORDER};
        border-radius: {T.RADIUS_SM}px;
        padding: {T.SPACE_SM}px {T.SPACE_MD}px;
        min-height: 36px;
    }}
    QLineEdit:focus {{ border: 2px solid {T.INTERACTIVE}; }}
    QLineEdit:read-only {{ background-color: {T.SURFACE_ALT}; }}
    QTabWidget::pane {{
        border: 1px solid {T.BORDER_LIGHT};
        border-radius: {T.RADIUS_SM}px;
        background-color: {T.SURFACE_LIGHT};
        margin-top: -1px;
    }}
    QTabBar::tab {{
        font-family: {T.FONT_FAMILY};
        font-size: {T.FONT_SIZE_SM}px;
        font-weight: 600;
        color: {T.TEXT_SECONDARY};
        background-color: transparent;
        border: none;
        border-bottom: 3px solid transparent;
        padding: 10px {T.SPACE_LG}px;
        margin-right: 4px;
        min-width: 100px;
        min-height: 20px;
    }}
    QTabBar::tab:selected {{
        color: {T.INTERACTIVE};
        border-bottom: 3px solid {T.INTERACTIVE};
    }}
    QTabBar::tab:hover {{
        color: {T.INTERACTIVE_HOVER};
        background-color: {T.INTERACTIVE_LIGHT};
    }}
    QProgressBar {{
        border: none;
        border-radius: {T.RADIUS_SM}px;
        background-color: {T.BORDER_LIGHT};
        text-align: center;
        font-size: {T.FONT_SIZE_SM}px;
        color: {T.TEXT_PRIMARY};
        min-height: 24px;
    }}
    QProgressBar::chunk {{
        background-color: {T.INTERACTIVE};
        border-radius: {T.RADIUS_SM}px;
    }}
    QTreeWidget {{
        font-family: {T.FONT_FAMILY};
        font-size: {T.FONT_SIZE_SM}px;
        border: 1px solid {T.BORDER_LIGHT};
        border-radius: {T.RADIUS_SM}px;
        background-color: {T.SURFACE_LIGHT};
        alternate-background-color: {T.SURFACE_ALT};
    }}
    QTreeWidget::item {{ padding: 4px 8px; min-height: 28px; }}
    QTreeWidget::item:selected {{
        background-color: {T.INTERACTIVE_LIGHT};
        color: {T.TEXT_PRIMARY};
    }}
    QHeaderView::section {{
        font-family: {T.FONT_FAMILY};
        font-size: {T.FONT_SIZE_SM}px;
        font-weight: 600;
        color: {T.TEXT_PRIMARY};
        background-color: {T.SURFACE_ALT};
        border: none;
        border-bottom: 2px solid {T.BORDER};
        padding: 6px 8px;
    }}
    QTextEdit {{
        font-family: {T.FONT_FAMILY};
        font-size: {T.FONT_SIZE_SM}px;
        color: {T.TEXT_PRIMARY};
        background-color: {T.SURFACE_LIGHT};
        border: 1px solid {T.BORDER_LIGHT};
        border-radius: {T.RADIUS_SM}px;
        padding: {T.SPACE_SM}px;
    }}
    QTextEdit QScrollBar:vertical {{
        background: {T.SURFACE_ALT};
        width: 12px;
        margin: 0px;
        border-radius: 6px;
    }}
    QTextEdit QScrollBar::handle:vertical {{
        background: {T.BORDER};
        min-height: 30px;
        border-radius: 6px;
    }}
    QTextEdit QScrollBar::handle:vertical:hover {{
        background: {T.TEXT_SECONDARY};
    }}
    QTextEdit QScrollBar::add-line:vertical,
    QTextEdit QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QFrame#headerFrame {{
        background-color: {T.SURFACE_DARK};
        border-radius: {T.RADIUS_SM}px;
    }}
    QFrame#divider {{
        background-color: {T.DIVIDER};
        max-height: 1px;
        min-height: 1px;
    }}
    """


class ValidationDialog(QDialog):
    """Main dialog - SICAR AD: Validate Environmental Dataset Structure."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SICAR AD — Validate Environmental Dataset Structure")
        self.setMinimumSize(960, 680)
        self.report = None
        self.setStyleSheet(_govbr_stylesheet())
        self.setup_ui()

    def setup_ui(self):
        """Builds the interface with compact header + unified tabs."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # --- Compact header (dark background) ---
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 10, 16, 10)
        header_layout.setSpacing(2)

        title_label = QLabel("SICAR AD — Validate Environmental Dataset Structure")
        title_label.setObjectName("headerTitle")
        header_layout.addWidget(title_label)

        subtitle_label = QLabel(
            "ISO 19157:2013 · Geographic Data Quality · Logical Consistency"
        )
        subtitle_label.setObjectName("headerSubtitle")
        header_layout.addWidget(subtitle_label)

        layout.addWidget(header_frame)

        # --- Unified tabs ---
        self.tabs = QTabWidget()
        self.tabs.setSizePolicy(_SP_EXPANDING, _SP_EXPANDING)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.setElideMode(Qt.TextElideMode.ElideNone if hasattr(Qt, 'TextElideMode') else Qt.ElideNone)

        # Tab: Source Dataset
        self.tab_source = QWidget()
        self._setup_tab_source()
        self.tabs.addTab(self.tab_source, "Select Dataset")

        # Tab: Rules
        self.tab_rules = QWidget()
        self._setup_tab_rules()
        self.tabs.addTab(self.tab_rules, "Rules")

        # Tab: Results (hidden until validation)
        self.tab_results = QWidget()
        self._setup_tab_results()

        # Tab: Log (hidden until validation)
        self.tab_log = QWidget()
        self._setup_tab_log()

        layout.addWidget(self.tabs)

        # --- Footer ---
        footer_divider = QFrame()
        footer_divider.setObjectName("divider")
        layout.addWidget(footer_divider)


    # ------------------------------------------------------------------
    # Tab: Source Dataset (selection + validate button)
    # ------------------------------------------------------------------

    def _setup_tab_source(self):
        """Sets up the Source Dataset tab."""
        layout = QVBoxLayout(self.tab_source)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        file_hint = QLabel(
            "Select the GeoPackage (.gpkg) file or GeoDatabase (.gdb) directory "
            "of the environmental dataset to be validated."
        )
        file_hint.setWordWrap(True)
        file_hint.setStyleSheet(
            f"color: {GovBRTokens.TEXT_SECONDARY}; "
            f"font-size: {GovBRTokens.FONT_SIZE_SM}px;"
        )
        layout.addWidget(file_hint)

        # Input + buttons
        file_row = QHBoxLayout()
        file_row.setSpacing(8)

        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("No file selected...")
        self.file_input.setReadOnly(True)
        file_row.addWidget(self.file_input, 1)

        btn_gpkg = QPushButton("Select .GPKG")
        btn_gpkg.setObjectName("secondaryBtn")
        btn_gpkg.setCursor(_CURSOR_POINTING)
        btn_gpkg.clicked.connect(self._browse_gpkg)
        file_row.addWidget(btn_gpkg)

        btn_gdb = QPushButton("Select .GDB")
        btn_gdb.setObjectName("secondaryBtn")
        btn_gdb.setCursor(_CURSOR_POINTING)
        btn_gdb.clicked.connect(self._browse_gdb)
        file_row.addWidget(btn_gdb)

        layout.addLayout(file_row)

        # Row: "Validate Layer" checkbox + layer ComboBox + Detailed Validation
        layer_filter_row = QHBoxLayout()
        layer_filter_row.setContentsMargins(0, 4, 0, 4)
        layer_filter_row.setSpacing(4)

        self.chk_layer_filter = QCheckBox("Validate Layer")
        self.chk_layer_filter.setEnabled(False)
        self.chk_layer_filter.setStyleSheet("font-weight: 600;")
        self.chk_layer_filter.stateChanged.connect(self._on_layer_filter_toggled)
        layer_filter_row.addWidget(self.chk_layer_filter)

        self.cmb_layer_filter = QComboBox()
        self.cmb_layer_filter.setEnabled(False)
        self.cmb_layer_filter.setMinimumWidth(220)
        self.cmb_layer_filter.addItem("")
        for layer_name in EXPECTED_LAYERS:
            self.cmb_layer_filter.addItem(layer_name)
        self.cmb_layer_filter.currentIndexChanged.connect(self._on_layer_combo_changed)
        layer_filter_row.addWidget(self.cmb_layer_filter)

        self.chk_detailed = QCheckBox("Detailed Validation")
        self.chk_detailed.setEnabled(False)
        self.chk_detailed.setStyleSheet("font-weight: 600;")
        self.chk_detailed.stateChanged.connect(self._on_detailed_toggled)
        layer_filter_row.addWidget(self.chk_detailed)

        self.lbl_error_limit = QLabel("Max errors to list")
        self.lbl_error_limit.setEnabled(False)
        self.lbl_error_limit.setStyleSheet(
            f"font-weight: 600; color: {GovBRTokens.TEXT_SECONDARY};"
        )
        layer_filter_row.addWidget(self.lbl_error_limit)

        self.txt_error_limit = QLineEdit()
        self.txt_error_limit.setPlaceholderText("e.g.: 10")
        self.txt_error_limit.setText("10")
        self.txt_error_limit.setEnabled(False)
        self.txt_error_limit.setFixedWidth(50)
        self.txt_error_limit.setMaximumHeight(28)
        self.txt_error_limit.setAlignment(_ALIGN_CENTER)
        self.txt_error_limit.setValidator(QIntValidator(1, 1000, self))
        self.txt_error_limit.setStyleSheet(
            f"border: 1px solid {GovBRTokens.BORDER}; "
            f"border-radius: {GovBRTokens.RADIUS_SM}px; "
            f"padding: 2px 4px; "
            f"font-size: {GovBRTokens.FONT_SIZE_SM}px;"
        )
        layer_filter_row.addWidget(self.txt_error_limit)

        layer_filter_row.addStretch()
        layout.addLayout(layer_filter_row)

        # Validate button
        btn_row = QHBoxLayout()
        self.btn_validate = QPushButton("▶  Validate Dataset 1857")
        self.btn_validate.setObjectName("primaryBtn")
        self.btn_validate.setCursor(_CURSOR_POINTING)
        self.btn_validate.setEnabled(False)
        self.btn_validate.setMinimumHeight(44)
        self.btn_validate.setMinimumWidth(200)
        self.btn_validate.clicked.connect(self.run_validation)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_validate)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Progress bar (below Validate button)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setObjectName("progressLabel")
        self.progress_label.setAlignment(_ALIGN_CENTER)
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)

        layout.addStretch()


    # ------------------------------------------------------------------
    # Tab: Rules
    # ------------------------------------------------------------------

    def _setup_tab_rules(self):
        """Sets up the tab with ISO 19157 validation rules."""
        layout = QVBoxLayout(self.tab_rules)
        layout.setContentsMargins(12, 12, 12, 12)

        rules_text = QTextBrowser()
        rules_text.setOpenExternalLinks(True)
        rules_text.setSizePolicy(_SP_EXPANDING, _SP_EXPANDING)
        rules_text.setHtml(self._get_rules_html())
        layout.addWidget(rules_text)

    def _get_rules_html(self) -> str:
        """HTML of the validation rules + layer subclassification."""
        T = GovBRTokens
        tbl = f"border-collapse: collapse; width: 100%; font-size: {T.FONT_SIZE_SM}px;"
        th = f"padding: 6px 10px; text-align: left; border-bottom: 2px solid {T.BORDER};"
        td = f"padding: 6px 10px; border-bottom: 1px solid {T.BORDER_LIGHT};"

        return f"""
        <div style="font-family: {T.FONT_FAMILY}; color: {T.TEXT_PRIMARY};
                    font-size: {T.FONT_SIZE_SM}px; line-height: 1.5;">

        <h2 style="color: {T.SURFACE_DARK}; font-weight: 600; font-size: 14px;">
            ISO 19157:2013 — Geographic Data Quality</h2>
        <p>The ISO 19157 / 2013 standard defines quality elements for evaluating geographic data.
        This validator applies <b>Logical Consistency</b> checks (section 7.3.3 of the standard) that
        assess whether the state dataset structure meets the minimum criteria to integrate the
        SICAR AD environmental dataset.</p>

        <div style="background-color: {T.INFO_BG}; border-left: 4px solid {T.INFO};
                    padding: 12px 16px; border-radius: 4px; margin: 12px 0;">
            <b style="color: {T.INFO};">ℹ Layout configuration</b><br>
            The environmental dataset structure (expected layers, required fields,
            class intervals and coordinate system) is defined in the
            <b>geodb-layout.json</b> file located in the plugin directory.
            To change the environmental dataset structure, edit this file.
        </div>

        {self._get_references_html()}

        <hr style="border: none; border-top: 1px solid {T.DIVIDER}; margin: 12px 0;">

        <h3 style="color: {T.INTERACTIVE}; font-weight: 600; font-size: 13px;">
            1. Format Consistency</h3>
        <table style="{tbl}">
        <tr style="background: {T.SURFACE_ALT};"><th style="{th}">Rule</th>
            <th style="{th}">Description</th></tr>
        <tr><td style="{td}">Dataset format</td>
            <td style="{td}">GeoPackage (.gpkg) or ESRI File Geodatabase (.gdb)</td></tr>
        <tr><td style="{td}">Dataset readability</td>
            <td style="{td}">Readable and with at least one layer</td></tr>
        </table>

        <h3 style="color: {T.INTERACTIVE}; font-weight: 600; font-size: 13px; margin-top: 14px;">
            2. Conceptual Consistency</h3>
        <table style="{tbl}">
        <tr style="background: {T.SURFACE_ALT};"><th style="{th}">Rule</th>
            <th style="{th}">Description</th></tr>
        <tr><td style="{td}">Layer names</td><td style="{td}">Expected layers (APP, AREA_ANTROPIZADA, AREA_CONSOLIDADA, HIDROGRAFIA, VEGETACAO_2008, VEGETACAO_ATUAL, SERVIDAO, RELEVO, USO_RESTRITO, APP_ESPECIAL)</td></tr>
        <tr><td style="{td}">Records</td><td style="{td}">At least 1 record per layer</td></tr>
        <tr><td style="{td}">CLASSE attribute</td><td style="{td}">Presence/absence of layer subclassification attribute</td></tr>
        <tr><td style="{td}">CRS</td><td style="{td}">Expected coordinate system - SIRGAS 2000 (EPSG:4674)</td></tr>
        </table>

        <h3 style="color: {T.INTERACTIVE}; font-weight: 600; font-size: 13px; margin-top: 14px;">
            3. Domain Consistency</h3>
        <table style="{tbl}">
        <tr style="background: {T.SURFACE_ALT};"><th style="{th}">Rule</th>
            <th style="{th}">Description</th></tr>
        <tr><td style="{td}">Numeric type</td><td style="{td}">CLASSE attribute is numeric</td></tr>
        <tr><td style="{td}">Null values</td><td style="{td}">No null values</td></tr>
        <tr><td style="{td}">Domain</td><td style="{td}">Values within expected interval</td></tr>
        </table>

        <h3 style="color: {T.INTERACTIVE}; font-weight: 600; font-size: 13px; margin-top: 14px;">
            4. Topological Consistency</h3>
        <table style="{tbl}">
        <tr style="background: {T.SURFACE_ALT};"><th style="{th}">Rule</th>
            <th style="{th}">Description</th></tr>
        <tr><td style="{td}">Null/empty geometries</td><td style="{td}">Null or empty geometries are not allowed</td></tr>
        <tr><td style="{td}">Topological errors</td><td style="{td}">Valid geometries</td></tr>
        <tr><td style="{td}">2D geometries</td><td style="{td}">Geometries must be two-dimensional (no Z coordinate)</td></tr>
        </table>

        <hr style="border: none; border-top: 1px solid {T.DIVIDER}; margin: 16px 0;">

        <h3 style="color: {T.INTERACTIVE}; font-weight: 600; font-size: 13px;">
            Layer Subclassification (CLASSE attribute)</h3>

        <h4 style="margin: 10px 0 4px 0; font-size: 12px;">APP (Classes 1 to 8)</h4>
        <table style="{tbl}">
        <tr style="background: {T.SURFACE_ALT};"><th style="{th}">Class</th>
            <th style="{th}">Description</th></tr>
        <tr><td style="{td}">1</td><td style="{td}">APP_RIO_ATE_10</td></tr>
        <tr><td style="{td}">2</td><td style="{td}">APP_RIO_10_A_50</td></tr>
        <tr><td style="{td}">3</td><td style="{td}">APP_RIO_50_A_200</td></tr>
        <tr><td style="{td}">4</td><td style="{td}">APP_RIO_200_A_600</td></tr>
        <tr><td style="{td}">5</td><td style="{td}">APP_RIO_ACIMA_600</td></tr>
        <tr><td style="{td}">6</td><td style="{td}">APP_LAGO_NATURAL</td></tr>
        <tr><td style="{td}">7</td><td style="{td}">APP_RESERVATORIO_ARTIFICIAL</td></tr>
        <tr><td style="{td}">8</td><td style="{td}">APP_NASCENTE</td></tr>
        </table>

        <h4 style="margin: 10px 0 4px 0; font-size: 12px;">HIDROGRAFIA (Classes 1 to 8)</h4>
        <table style="{tbl}">
        <tr style="background: {T.SURFACE_ALT};"><th style="{th}">Class</th>
            <th style="{th}">Description</th></tr>
        <tr><td style="{td}">1</td><td style="{td}">RIO_ATE_10</td></tr>
        <tr><td style="{td}">2</td><td style="{td}">RIO_10_A_50</td></tr>
        <tr><td style="{td}">3</td><td style="{td}">RIO_50_A_200</td></tr>
        <tr><td style="{td}">4</td><td style="{td}">RIO_200_A_600</td></tr>
        <tr><td style="{td}">5</td><td style="{td}">RIO_ACIMA_600</td></tr>
        <tr><td style="{td}">6</td><td style="{td}">LAGO_NATURAL</td></tr>
        <tr><td style="{td}">7</td><td style="{td}">RESERVATORIO_ARTIFICIAL</td></tr>
        <tr><td style="{td}">8</td><td style="{td}">NASCENTE</td></tr>
        </table>

        <h4 style="margin: 10px 0 4px 0; font-size: 12px;">USO_RESTRITO (Classes 1 to 2)</h4>
        <table style="{tbl}">
        <tr style="background: {T.SURFACE_ALT};"><th style="{th}">Class</th>
            <th style="{th}">Description</th></tr>
        <tr><td style="{td}">1</td><td style="{td}">DECLIVIDADE_25_A_45</td></tr>
        <tr><td style="{td}">2</td><td style="{td}">PANTANEIRA</td></tr>
        </table>

        <h4 style="margin: 10px 0 4px 0; font-size: 12px;">SERVIDAO (Classes 1 to 4)</h4>
        <table style="{tbl}">
        <tr style="background: {T.SURFACE_ALT};"><th style="{th}">Class</th>
            <th style="{th}">Description</th></tr>
        <tr><td style="{td}">1</td><td style="{td}">INFRAESTRUTURA_PUBLICA</td></tr>
        <tr><td style="{td}">2</td><td style="{td}">UTILIDADE_PUBLICA</td></tr>
        <tr><td style="{td}">3</td><td style="{td}">RESERVATORIO_ABASTECIMENTO_GERACAO_ENERGIA</td></tr>
        <tr><td style="{td}">4</td><td style="{td}">ENTORNO_RESERVATORIO_ABASTECIMENTO_GERACAO_ENERGIA</td></tr>
        </table>

        <h4 style="margin: 10px 0 4px 0; font-size: 12px;">RELEVO (Classes 1 to 8)</h4>
        <table style="{tbl}">
        <tr style="background: {T.SURFACE_ALT};"><th style="{th}">Class</th>
            <th style="{th}">Description</th></tr>
        <tr><td style="{td}">1</td><td style="{td}">ALTITUDE_SUPERIOR_1800</td></tr>
        <tr><td style="{td}">2</td><td style="{td}">BORDA_CHAPADA</td></tr>
        <tr><td style="{td}">3</td><td style="{td}">DECLIVIDADE_MAIOR_45</td></tr>
        <tr><td style="{td}">4</td><td style="{td}">TOPO_MORRO</td></tr>
        <tr><td style="{td}">5</td><td style="{td}">APP_ALTITUDE_SUPERIOR_1800</td></tr>
        <tr><td style="{td}">6</td><td style="{td}">APP_BORDA_CHAPADA</td></tr>
        <tr><td style="{td}">7</td><td style="{td}">APP_DECLIVIDADE_MAIOR_45</td></tr>
        <tr><td style="{td}">8</td><td style="{td}">APP_TOPO_MORRO</td></tr>
        </table>

        <h4 style="margin: 10px 0 4px 0; font-size: 12px;">APP_ESPECIAL (Classes 1 to 10)</h4>
        <table style="{tbl}">
        <tr style="background: {T.SURFACE_ALT};"><th style="{th}">Class</th>
            <th style="{th}">Description</th></tr>
        <tr><td style="{td}">1</td><td style="{td}">RESERVATORIO_ENERGIA_24082001</td></tr>
        <tr><td style="{td}">2</td><td style="{td}">VEGETACAO_RESTINGA</td></tr>
        <tr><td style="{td}">3</td><td style="{td}">VEGETACAO_VEREDA</td></tr>
        <tr><td style="{td}">4</td><td style="{td}">VEGETACAO_BANHADO</td></tr>
        <tr><td style="{td}">5</td><td style="{td}">VEGETACAO_MANGUEZAL</td></tr>
        <tr><td style="{td}">6</td><td style="{td}">APP_RESERVATORIO_ENERGIA_24082001</td></tr>
        <tr><td style="{td}">7</td><td style="{td}">APP_RESTINGA</td></tr>
        <tr><td style="{td}">8</td><td style="{td}">APP_VEREDA</td></tr>
        <tr><td style="{td}">9</td><td style="{td}">APP_BANHADO</td></tr>
        <tr><td style="{td}">10</td><td style="{td}">APP_MANGUEZAL</td></tr>
        </table>

        </div>
        """

    def _get_references_html(self) -> str:
        """Generates HTML of the normative references box from plugin-config.json."""
        if not REFERENCES:
            return ""

        T = GovBRTokens
        ref = REFERENCES[0]
        ref_title = ref.get("title", "")
        ref_url = ref.get("url", "")

        if not ref_title or not ref_url:
            return ""

        return (
            f"<div style='background-color: {T.SURFACE_ALT}; border: 1px solid {T.BORDER_LIGHT}; "
            f"padding: 12px 16px; border-radius: 4px; margin: 12px 0;'>"
            f"The validator also follows the guidelines of the Technical Note "
            f"\"<a href='{ref_url}' style='color: {T.INTERACTIVE}; font-weight: 600;'>"
            f"{ref_title}</a>\"."
            f"</div>"
        )


    # ------------------------------------------------------------------
    # Tab: Results
    # ------------------------------------------------------------------

    def _setup_tab_results(self):
        """Sets up the results tab with sub-tabs per consistency category."""
        layout = QVBoxLayout(self.tab_results)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.summary_text = QTextBrowser()
        self.summary_text.setOpenExternalLinks(False)
        self.summary_text.setMaximumHeight(220)
        self.summary_text.setSizePolicy(_SP_EXPANDING, QSizePolicy.Maximum if hasattr(QSizePolicy, 'Maximum') else QSizePolicy.Policy.Maximum)
        layout.addWidget(self.summary_text)

        self.sub_tabs = QTabWidget()
        self.sub_tabs.setSizePolicy(_SP_EXPANDING, _SP_EXPANDING)

        self.tab_format = QWidget()
        self.tree_format = self._make_tree(self.tab_format, ["Check", "Status", "Details"])
        self.sub_tabs.addTab(self.tab_format, "Format Consistency")

        self.tab_conceptual = QWidget()
        self.tree_conceptual = self._make_tree(
            self.tab_conceptual, ["Layer", "Check", "Status", "Details"]
        )
        self.sub_tabs.addTab(self.tab_conceptual, "Conceptual Consistency")

        self.tab_domain = QWidget()
        self.tree_domain = self._make_tree(
            self.tab_domain, ["Layer", "Check", "Status", "Details"]
        )
        self.sub_tabs.addTab(self.tab_domain, "Domain Consistency")

        self.tab_topological = QWidget()
        self.tree_topological = self._make_tree(
            self.tab_topological, ["Layer", "Check", "Status", "Details"]
        )
        self.sub_tabs.addTab(self.tab_topological, "Topological Consistency")

        layout.addWidget(self.sub_tabs)

        # Export PDF button (inside Results tab)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()
        self.btn_export_pdf = QPushButton("Export PDF")
        self.btn_export_pdf.setObjectName("secondaryBtn")
        self.btn_export_pdf.setCursor(_CURSOR_POINTING)
        self.btn_export_pdf.clicked.connect(self.export_pdf)
        btn_row.addWidget(self.btn_export_pdf)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _make_tree(self, parent: QWidget, headers: list) -> QTreeWidget:
        """Creates a QTreeWidget inside parent."""
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(4, 4, 4, 4)
        tree = QTreeWidget()
        tree.setHeaderLabels(headers)
        tree.setColumnWidth(0, 200)
        if len(headers) > 4:
            tree.setColumnWidth(1, 180)
            tree.setColumnWidth(2, 140)
            tree.setColumnWidth(3, 300)
            tree.setColumnWidth(4, 400)
        elif len(headers) > 3:
            tree.setColumnWidth(1, 180)
            tree.setColumnWidth(2, 140)
        else:
            tree.setColumnWidth(1, 140)
        tree.setAlternatingRowColors(True)
        tree.setRootIsDecorated(False)
        tree.setSortingEnabled(True)
        tree.setSizePolicy(_SP_EXPANDING, _SP_EXPANDING)
        layout.addWidget(tree)
        return tree


    # ------------------------------------------------------------------
    # Tab: Log
    # ------------------------------------------------------------------

    def _setup_tab_log(self):
        """Sets up the log tab."""
        layout = QVBoxLayout(self.tab_log)
        layout.setContentsMargins(12, 12, 12, 12)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn if hasattr(Qt, 'ScrollBarPolicy') else Qt.ScrollBarAlwaysOn)
        self.log_text.setStyleSheet(
            f"font-family: 'Consolas', 'Courier New', monospace; "
            f"font-size: {GovBRTokens.FONT_SIZE_XS}px; "
            f"background-color: {GovBRTokens.SURFACE_LIGHT}; "
            f"color: {GovBRTokens.TEXT_PRIMARY}; "
            f"border-radius: {GovBRTokens.RADIUS_SM}px; "
            f"padding: {GovBRTokens.SPACE_SM}px;"
        )
        self.log_text.setSizePolicy(_SP_EXPANDING, _SP_EXPANDING)
        layout.addWidget(self.log_text)


    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _browse_gpkg(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select GeoPackage", "",
            "GeoPackage (*.gpkg *.gpkg.zip *.zip);;All (*)",
        )
        if filepath:
            self.file_input.setText(filepath)
            self.btn_validate.setEnabled(True)
            self.chk_layer_filter.setEnabled(True)
            self._hide_results()

    def _browse_gdb(self):
        dirpath = QFileDialog.getExistingDirectory(
            self, "Select .gdb folder", "", _SHOW_DIRS_ONLY,
        )
        if dirpath:
            if dirpath.lower().endswith(".gdb"):
                self.file_input.setText(dirpath)
                self.btn_validate.setEnabled(True)
                self.chk_layer_filter.setEnabled(True)
                self._hide_results()
            else:
                QMessageBox.warning(
                    self, "Invalid format",
                    "The selected folder does not end with .gdb.",
                )

    def _on_layer_filter_toggled(self, state):
        """Enables/disables the layer combobox according to the checkbox."""
        enabled = int(state) == int(_QT_CHECKED)
        self.cmb_layer_filter.setEnabled(enabled)
        if not enabled:
            self.cmb_layer_filter.setCurrentIndex(0)
            self.chk_detailed.setChecked(False)
            self.chk_detailed.setEnabled(False)
            self.lbl_error_limit.setEnabled(False)
            self.txt_error_limit.setEnabled(False)
        else:
            self._update_detailed_checkbox_state()

    def _on_detailed_toggled(self, state):
        """Validates whether the Detailed Validation checkbox can be checked."""
        checked = int(state) == int(_QT_CHECKED)
        if checked:
            if not self.chk_layer_filter.isChecked() or not self.cmb_layer_filter.currentText().strip():
                self.chk_detailed.setChecked(False)
                QMessageBox.warning(
                    self,
                    "Detailed Validation",
                    "Detailed Validation can only be run on a single layer.",
                )
                return
        self.lbl_error_limit.setEnabled(checked)
        self.txt_error_limit.setEnabled(checked)

    def _update_detailed_checkbox_state(self):
        """Updates the enabled state of the Detailed Validation checkbox."""
        can_enable = (
            self.chk_layer_filter.isChecked()
            and self.cmb_layer_filter.currentText().strip() != ""
        )
        self.chk_detailed.setEnabled(can_enable)
        if not can_enable:
            self.chk_detailed.setChecked(False)

    def _on_layer_combo_changed(self, index):
        """Updates the Detailed Validation checkbox state when the selected layer changes."""
        self._update_detailed_checkbox_state()

    def _hide_results(self):
        for tab in (self.tab_results, self.tab_log):
            idx = self.tabs.indexOf(tab)
            if idx >= 0:
                self.tabs.removeTab(idx)

    def _show_results(self):
        if self.tabs.indexOf(self.tab_results) < 0:
            self.tabs.addTab(self.tab_results, "Results")
        if self.tabs.indexOf(self.tab_log) < 0:
            self.tabs.addTab(self.tab_log, "Log")
        self.tabs.setCurrentWidget(self.tab_results)

    def _log_diagnostics(self, base_path: str):
        """Displays environment diagnostics at the start of the log (cross-platform)."""
        import os
        import sys
        import platform
        from pathlib import Path

        T = GovBRTokens
        header_style = f"color: {T.INTERACTIVE}; font-weight: 600;"
        label_style = f"color: {T.TEXT_SECONDARY};"
        value_style = f"color: {T.TEXT_PRIMARY};"

        lines = []
        lines.append(f"<span style='{header_style}'>═══ Environment Diagnostics ═══</span>")

        lines.append(f"<br><span style='{header_style}'>▸ Input</span>")
        try:
            p = Path(base_path)
            if p.is_file():
                size_bytes = p.stat().st_size
                size_str = f"{size_bytes / 1024:.1f} KB" if size_bytes < 1024 * 1024 else f"{size_bytes / (1024 * 1024):.1f} MB"
                lines.append(f"  <span style='{label_style}'>File:</span> <span style='{value_style}'>{p.name} ({size_str})</span>")
            elif p.is_dir():
                total = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                size_str = f"{total / (1024 * 1024):.1f} MB"
                lines.append(f"  <span style='{label_style}'>Directory:</span> <span style='{value_style}'>{p.name} ({size_str})</span>")
            else:
                lines.append(f"  <span style='{label_style}'>Path:</span> <span style='{value_style}'>{base_path}</span>")
        except Exception:
            lines.append(f"  <span style='{label_style}'>Path:</span> <span style='{value_style}'>{base_path}</span>")

        lines.append(f"<br><span style='{header_style}'>▸ Software</span>")
        try:
            from qgis.core import Qgis
            qgis_version = Qgis.QGIS_VERSION
        except Exception:
            qgis_version = "N/A"
        lines.append(f"  <span style='{label_style}'>QGIS:</span> <span style='{value_style}'>{qgis_version}</span>")
        lines.append(f"  <span style='{label_style}'>Python:</span> <span style='{value_style}'>{sys.version.split()[0]}</span>")

        libs = {}
        for lib_name in ("geopandas", "pyogrio", "shapely"):
            try:
                mod = __import__(lib_name)
                libs[lib_name] = getattr(mod, "__version__", "?")
            except ImportError:
                libs[lib_name] = "not installed"
        libs_str = " | ".join(f"{k} {v}" for k, v in libs.items())
        lines.append(f"  <span style='{label_style}'>Libraries:</span> <span style='{value_style}'>{libs_str}</span>")

        lines.append(f"<br><span style='{header_style}'>▸ System</span>")
        os_info = f"{platform.system()} {platform.release()}"
        lines.append(f"  <span style='{label_style}'>OS:</span> <span style='{value_style}'>{os_info}</span>")
        lines.append(f"  <span style='{label_style}'>Encoding:</span> <span style='{value_style}'>{sys.getfilesystemencoding()}</span>")

        lines.append(f"<br><span style='{header_style}'>▸ Hardware</span>")
        cpu_name = self._get_cpu_name()
        cpu_count = os.cpu_count() or 0
        lines.append(f"  <span style='{label_style}'>CPU:</span> <span style='{value_style}'>{cpu_name} ({cpu_count} cores)</span>")

        ram_info = self._get_ram_info()
        lines.append(f"  <span style='{label_style}'>RAM:</span> <span style='{value_style}'>{ram_info}</span>")

        lines.append(f"<br><span style='{header_style}'>═══════════════════════════════</span>")
        lines.append("")
        self.log_text.setHtml("<br>".join(lines))

    def _get_cpu_name(self) -> str:
        """Gets the commercial processor name (cross-platform, no subprocess)."""
        import platform
        if platform.system() == "Windows":
            try:
                import winreg
                reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
                cpu_name, _ = winreg.QueryValueEx(reg_key, "ProcessorNameString")
                winreg.CloseKey(reg_key)
                return cpu_name.strip()
            except Exception:
                pass
        if platform.system() == "Linux":
            try:
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if line.startswith("model name"):
                            return line.split(":", 1)[1].strip()
            except Exception:
                pass
        return platform.processor() or "N/A"

    def _get_ram_info(self) -> str:
        """Gets RAM information (cross-platform, no subprocess)."""
        import platform
        try:
            import psutil
            mem = psutil.virtual_memory()
            return f"{mem.total / (1024**3):.1f} GB total, {mem.available / (1024**3):.1f} GB available ({mem.percent:.0f}% in use)"
        except ImportError:
            pass
        if platform.system() == "Windows":
            try:
                import ctypes
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]
                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(stat)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
                return f"{stat.ullTotalPhys / (1024**3):.1f} GB total, {stat.ullAvailPhys / (1024**3):.1f} GB available ({stat.dwMemoryLoad}% in use)"
            except Exception:
                pass
        if platform.system() == "Linux":
            try:
                with open("/proc/meminfo", "r") as f:
                    info = {}
                    for line in f:
                        parts = line.split(":")
                        if len(parts) == 2:
                            key = parts[0].strip()
                            val = parts[1].strip().split()[0]
                            if key in ("MemTotal", "MemAvailable"):
                                info[key] = int(val)
                    if "MemTotal" in info:
                        total_gb = info["MemTotal"] / (1024 * 1024)
                        avail_gb = info.get("MemAvailable", 0) / (1024 * 1024)
                        pct = 100 - (avail_gb / total_gb * 100) if total_gb > 0 else 0
                        return f"{total_gb:.1f} GB total, {avail_gb:.1f} GB available ({pct:.0f}% in use)"
            except Exception:
                pass
        return "N/A"


    def run_validation(self):
        import time

        base_path = self.file_input.text()
        if not base_path:
            return

        layer_filter = None
        if self.chk_layer_filter.isChecked():
            layer_filter = self.cmb_layer_filter.currentText().strip()
            if not layer_filter:
                QMessageBox.warning(
                    self, "No layer selected",
                    "Select a layer to run the validation.",
                )
                return

        self._clear_results()

        if self.tabs.indexOf(self.tab_log) < 0:
            self.tabs.addTab(self.tab_log, "Log")

        detailed = self.chk_detailed.isChecked()
        error_limit = None
        if detailed:
            txt_limit = self.txt_error_limit.text().strip()
            if not txt_limit:
                QMessageBox.warning(
                    self,
                    "Error limit not defined",
                    "Error count limit not defined. "
                    "Processing may be extremely slow.",
                )
            else:
                error_limit = int(txt_limit)

        self._log_diagnostics(base_path)

        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.btn_validate.setEnabled(False)
        QCoreApplication.processEvents()

        t0 = time.time()
        try:
            self.report = validate_dataset(
                base_path,
                progress_callback=self._update_progress,
                layer_filter=layer_filter,
                detailed=detailed,
                error_limit=error_limit,
            )
        except Exception as e:
            self.progress_bar.setVisible(False)
            self.progress_label.setVisible(False)
            self.btn_validate.setEnabled(True)
            QMessageBox.critical(self, "Error", f"Validation error:\n{e}")
            return

        elapsed = time.time() - t0
        self.log_text.append(
            f"\n<span style='color: {GovBRTokens.SUCCESS}; font-weight: 600;'>[COMPLETED]</span> "
            f"Total time: {elapsed:.1f}s"
        )

        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.btn_validate.setEnabled(True)

        self._current_layer_filter = layer_filter
        self._display_report(self.report)
        self._show_results()

    def _update_progress(self, percent: int, message: str = ""):
        import time
        if percent >= 0:
            self.progress_bar.setValue(percent)
        if message:
            self.progress_label.setText(message)
            ts = time.strftime("%H:%M:%S")
            self.log_text.append(
                f"<span style='color: {GovBRTokens.INTERACTIVE};'>[{ts}]</span> "
                f"<span style='color: {GovBRTokens.TEXT_PRIMARY};'>{message}</span>"
            )
        QCoreApplication.processEvents()

    def _clear_results(self):
        self.tree_format.clear()
        self.tree_conceptual.clear()
        self.tree_domain.clear()
        self.tree_topological.clear()
        self.summary_text.clear()
        self.log_text.clear()

    def _display_report(self, report: ValidationReport):
        self._fill_tree(self.tree_format, report.format_checks, False)
        self._fill_tree(self.tree_conceptual, report.conceptual_checks, True)
        self._fill_tree(self.tree_domain, report.domain_checks, True)

        if self.chk_detailed.isChecked():
            self.tree_topological.clear()
            self.tree_topological.setColumnCount(5)
            self.tree_topological.setHeaderLabels(["Layer", "Check", "Status", "Details", "WKT"])
            self.tree_topological.setColumnWidth(3, 300)
            self.tree_topological.setColumnWidth(4, 400)
            self._fill_tree_detailed(self.tree_topological, report.topological_checks)
            idx_topo = self.sub_tabs.indexOf(self.tab_topological)
            if idx_topo >= 0:
                self.sub_tabs.setTabText(idx_topo, "Detailed Topological Consistency")
            self.sub_tabs.setCurrentWidget(self.tab_topological)
        else:
            self.tree_topological.clear()
            self.tree_topological.setColumnCount(4)
            self.tree_topological.setHeaderLabels(["Layer", "Check", "Status", "Details"])
            self._fill_tree(self.tree_topological, report.topological_checks, True)
            idx_topo = self.sub_tabs.indexOf(self.tab_topological)
            if idx_topo >= 0:
                self.sub_tabs.setTabText(idx_topo, "Topological Consistency")

        self._fill_summary(report)

    def _fill_tree(self, tree: QTreeWidget, checks: list[CheckResult], with_layer: bool):
        tree.clear()
        for check in checks:
            item = QTreeWidgetItem()
            if with_layer:
                item.setText(0, check.layer)
                item.setText(1, check.name)
                item.setText(2, check.status.value)
                item.setText(3, check.details)
                scol = 2
            else:
                item.setText(0, check.name)
                item.setText(1, check.status.value)
                item.setText(2, check.details)
                scol = 1

            color = QColor(GovBRTokens.SUCCESS if check.status == Status.CONFORMANT
                           else GovBRTokens.WARNING_TEXT if check.status == Status.WARNING
                           else GovBRTokens.ERROR)
            item.setForeground(scol, color)
            tree.addTopLevelItem(item)

        for i in range(tree.columnCount()):
            tree.resizeColumnToContents(i)

    def _fill_tree_detailed(self, tree: QTreeWidget, checks: list[CheckResult]):
        """Fills the detailed tree with columns: Layer, Check, Status, Details, WKT."""
        tree.clear()
        for check in checks:
            item = QTreeWidgetItem()
            item.setText(0, check.layer)
            item.setText(1, check.name)
            item.setText(2, check.status.value)
            item.setText(3, check.details)
            item.setText(4, check.wkt if check.wkt else "")

            color = QColor(GovBRTokens.SUCCESS if check.status == Status.CONFORMANT
                           else GovBRTokens.WARNING_TEXT if check.status == Status.WARNING
                           else GovBRTokens.ERROR)
            item.setForeground(2, color)
            tree.addTopLevelItem(item)

        for i in range(tree.columnCount()):
            tree.resizeColumnToContents(i)

    def _fill_summary(self, report: ValidationReport):
        from .validator import list_layers, EXPECTED_LAYERS
        T = GovBRTokens
        html = []
        html.append(f"<div style='font-family: {T.FONT_FAMILY}; color: {T.TEXT_PRIMARY}; font-size: {T.FONT_SIZE_SM}px; line-height: 1.5;'>")

        if report.passed and not report.has_warnings:
            bg, border, icon, text, color = (T.SUCCESS_BG, T.SUCCESS, "✓", "CONFORMANT", T.SUCCESS)
        elif report.passed and report.has_warnings:
            bg, border, icon, text, color = (T.WARNING_BG, T.WARNING_TEXT, "⚠", "CONFORMANT WITH WARNINGS", T.WARNING_TEXT)
        else:
            bg, border, icon, text, color = (T.ERROR_BG, T.ERROR, "✗", "NON-CONFORMANT", T.ERROR)

        html.append(
            f"<div style='background: {bg}; border-left: 4px solid {border}; "
            f"padding: 10px 14px; border-radius: 4px; margin-bottom: 10px;'>"
            f"<span style='font-size: 16px; font-weight: 700; color: {color};'>{icon} {text}</span><br>"
            f"<span style='font-size: 11px; color: {T.TEXT_SECONDARY};'>{report.summary()}</span></div>"
        )

        source_text = report.file_path
        if getattr(self, '_current_layer_filter', None):
            source_text += (f" — layer <b style='text-transform: uppercase;'>"
                            f"{self._current_layer_filter.upper()}</b>")

        html.append(f"<p style='font-size: 11px; color: {T.TEXT_SECONDARY};'><b>Source:</b> {source_text}</p>")

        html.append(
            f"<table style='border-collapse: collapse; width: 100%; font-size: {T.FONT_SIZE_SM}px; margin-top: 6px;'>"
            f"<tr style='background: {T.SURFACE_ALT};'>"
            f"<th style='padding: 6px 10px; text-align: left; border-bottom: 2px solid {T.BORDER};'>Category</th>"
            f"<th style='padding: 6px 10px; text-align: left; border-bottom: 2px solid {T.BORDER};'>Status</th>"
            f"<th style='padding: 6px 10px; text-align: left; border-bottom: 2px solid {T.BORDER};'>Result</th></tr>"
        )
        for cat, info in report.summary_by_category().items():
            if info["status"] == Status.CONFORMANT:
                st = f"<span style='color: {T.SUCCESS}; font-weight: 600;'>✓ Conformant</span>"
                rbg = ""
            elif info["status"] == Status.WARNING:
                st = f"<span style='color: {T.WARNING_TEXT}; font-weight: 600;'>⚠ Warning</span>"
                rbg = f" style='background: {T.WARNING_BG};'"
            else:
                st = f"<span style='color: {T.ERROR}; font-weight: 600;'>✗ Non-conformant</span>"
                rbg = f" style='background: {T.ERROR_BG};'"
            html.append(
                f"<tr{rbg}><td style='padding: 6px 10px; border-bottom: 1px solid {T.BORDER_LIGHT};'>{cat}</td>"
                f"<td style='padding: 6px 10px; border-bottom: 1px solid {T.BORDER_LIGHT};'>{st}</td>"
                f"<td style='padding: 6px 10px; border-bottom: 1px solid {T.BORDER_LIGHT};'>"
                f"{info['conformant']}/{info['total']}</td></tr>"
            )
        html.append("</table>")

        try:
            layers = list_layers(Path(report.file_path))
            html.append(f"<h4 style='color: {T.TEXT_PRIMARY}; font-weight: 600; margin-top: 10px; font-size: 12px;'>Layers found in dataset</h4><div style='margin-bottom: 6px;'>")
            for c in layers:
                exp = any(c.upper() == e.upper() for e in EXPECTED_LAYERS)
                clr = T.SUCCESS if exp else T.TEXT_SECONDARY
                bdr = T.SUCCESS if exp else T.BORDER
                bbg = T.SUCCESS_BG if exp else T.SURFACE_ALT
                html.append(
                    f"<div style='background: {bbg}; border: 1px solid {bdr}; color: {clr}; border-radius: 3px; "
                    f"padding: 2px 8px; margin: 2px 0; font-size: 11px; font-weight: 600;'>{c}</div>"
                )
            html.append("</div>")
        except Exception:
            pass

        divs = [c for c in report.checks if c.status == Status.NON_CONFORMANT]
        if divs:
            html.append(
                f"<div style='background: {T.ERROR_BG}; border-left: 4px solid {T.ERROR}; "
                f"padding: 10px 14px; border-radius: 4px; margin-top: 10px;'>"
                f"<b style='color: {T.ERROR};'>Non-conformant items ({len(divs)})</b>"
                f"<ul style='margin: 4px 0; padding-left: 16px; font-size: 11px;'>"
            )
            for ch in divs[:15]:
                lyr = f" [{ch.layer}]" if ch.layer else ""
                html.append(f"<li><b>{ch.name}</b>{lyr}: {ch.details}</li>")
            if len(divs) > 15:
                html.append(f"<li><i>...and {len(divs)-15} more items</i></li>")
            html.append("</ul></div>")

        html.append("</div>")
        self.summary_text.setHtml("\n".join(html))

    # ------------------------------------------------------------------
    # Export PDF
    # ------------------------------------------------------------------

    def export_pdf(self):
        from datetime import datetime
        import os

        if self.report is None:
            QMessageBox.warning(self, "Warning", "Run the validation before exporting.")
            return

        date_str = datetime.now().strftime("%Y%m%d_%H%M")
        suggested_name = f"report_{date_str}.pdf"

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save PDF Report", suggested_name,
            "PDF (*.pdf);;All (*)",
        )
        if not filepath:
            return

        try:
            result_path = export_report_pdf(self.report, filepath)
            os.startfile(str(result_path))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error generating PDF:\n{e}")
