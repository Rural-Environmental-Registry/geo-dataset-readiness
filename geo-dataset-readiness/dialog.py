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

i18n: all user-visible strings are loaded from i18n/<locale>.json files.
To add a new language copy i18n/en_US.json → i18n/<locale>.json and translate.
"""

from pathlib import Path

from qgis.PyQt.QtCore import Qt, QCoreApplication
from qgis.PyQt.QtGui import QColor, QIntValidator
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QLineEdit, QTreeWidget, QTreeWidgetItem, QMessageBox, QProgressBar,
    QSizePolicy, QTabWidget, QWidget, QTextEdit, QFrame, QCheckBox,
    QComboBox, QTextBrowser,
)

from .validator import (
    validate_dataset, Status, ValidationReport, CheckResult,
    EXPECTED_LAYERS, export_report_pdf,
)

# ---------------------------------------------------------------------------
# Application configuration
# ---------------------------------------------------------------------------

import json as _json
import os as _os


def _load_plugin_config() -> dict:
    config_path = _os.path.join(_os.path.dirname(__file__), "plugin-config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return _json.load(f)
    except (FileNotFoundError, _json.JSONDecodeError):
        return {}


_PLUGIN_CONFIG = _load_plugin_config()
REFERENCES = _PLUGIN_CONFIG.get("references", [])

# ---------------------------------------------------------------------------
# i18n — all translations loaded from i18n/<locale>.json
# ---------------------------------------------------------------------------

from .i18n import I18n, available_locales, _load_catalogue as _i18n_load_catalogue


def _build_language_labels() -> dict[str, str]:
    labels: dict[str, str] = {}
    for loc in available_locales():
        meta = _i18n_load_catalogue(loc).get("_meta", {})
        labels[loc] = meta.get("flag", f"🌐 {loc[:2].upper()}")
    return labels


_LANGUAGE_LABELS: dict[str, str] = _build_language_labels()

# ---------------------------------------------------------------------------
# Qt compatibility shims
# ---------------------------------------------------------------------------

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
# Design Tokens — GOV.BR DS
# ---------------------------------------------------------------------------

class GovBRTokens:
    SURFACE_LIGHT = "#FFFFFF"; SURFACE_ALT = "#F8F8F8"; SURFACE_DARK = "#071D41"
    TEXT_PRIMARY = "#333333"; TEXT_SECONDARY = "#636363"; TEXT_ON_DARK = "#FFFFFF"
    INTERACTIVE = "#1351B4"; INTERACTIVE_HOVER = "#0C326F"; INTERACTIVE_LIGHT = "#D4E5FF"
    SUCCESS = "#168821"; SUCCESS_BG = "#E3F5E1"
    ERROR = "#E52207"; ERROR_BG = "#FDE0DB"
    WARNING = "#FFCD07"; WARNING_TEXT = "#D2600F"; WARNING_BG = "#FFF5C2"
    INFO = "#155BCB"; INFO_BG = "#D4E5FF"
    BORDER = "#CCCCCC"; BORDER_LIGHT = "#E6E6E6"; DIVIDER = "#E6E6E6"
    SPACE_XS = 4; SPACE_SM = 8; SPACE_MD = 16; SPACE_LG = 24
    RADIUS_SM = 4; RADIUS_MD = 8
    FONT_FAMILY = "Rawline, Roboto, 'Segoe UI', sans-serif"
    FONT_SIZE_XS = 11; FONT_SIZE_SM = 12; FONT_SIZE_MD = 14
    FONT_SIZE_LG = 16; FONT_SIZE_XL = 20


def _govbr_stylesheet() -> str:
    T = GovBRTokens
    return f"""
    QDialog {{ background-color:{T.SURFACE_LIGHT}; color:{T.TEXT_PRIMARY}; font-family:{T.FONT_FAMILY}; font-size:{T.FONT_SIZE_MD}px; }}
    QLabel {{ color:{T.TEXT_PRIMARY}; font-family:{T.FONT_FAMILY}; }}
    QLabel#headerTitle {{ color:{T.TEXT_ON_DARK}; font-size:{T.FONT_SIZE_XL}px; font-weight:600; }}
    QLabel#headerSubtitle {{ color:rgba(255,255,255,0.8); font-size:{T.FONT_SIZE_XS}px; }}
    QLabel#progressLabel {{ color:{T.TEXT_SECONDARY}; font-size:{T.FONT_SIZE_SM}px; }}
    QPushButton {{ font-family:{T.FONT_FAMILY}; font-size:{T.FONT_SIZE_MD}px; font-weight:600; border:none; border-radius:{T.RADIUS_SM}px; padding:{T.SPACE_SM}px {T.SPACE_LG}px; min-height:36px; }}
    QPushButton#primaryBtn {{ background-color:{T.INTERACTIVE}; color:{T.TEXT_ON_DARK}; }}
    QPushButton#primaryBtn:hover {{ background-color:{T.INTERACTIVE_HOVER}; }}
    QPushButton#primaryBtn:disabled {{ background-color:{T.BORDER}; color:{T.TEXT_SECONDARY}; }}
    QPushButton#secondaryBtn {{ background-color:transparent; color:{T.INTERACTIVE}; border:1px solid {T.INTERACTIVE}; }}
    QPushButton#secondaryBtn:hover {{ background-color:{T.INTERACTIVE_LIGHT}; }}
    QPushButton#secondaryBtn:disabled {{ background-color:{T.BORDER_LIGHT}; color:{T.TEXT_SECONDARY}; border:1px solid {T.BORDER}; }}
    QPushButton#tertiaryBtn {{ background-color:transparent; color:{T.INTERACTIVE}; border:none; }}
    QPushButton#tertiaryBtn:hover {{ background-color:{T.INTERACTIVE_LIGHT}; }}
    QLineEdit {{ font-family:{T.FONT_FAMILY}; font-size:{T.FONT_SIZE_MD}px; color:{T.TEXT_PRIMARY}; background-color:{T.SURFACE_LIGHT}; border:1px solid {T.BORDER}; border-radius:{T.RADIUS_SM}px; padding:{T.SPACE_SM}px {T.SPACE_MD}px; min-height:36px; }}
    QLineEdit:focus {{ border:2px solid {T.INTERACTIVE}; }}
    QLineEdit:read-only {{ background-color:{T.SURFACE_ALT}; }}
    QTabWidget::pane {{ border:1px solid {T.BORDER_LIGHT}; border-radius:{T.RADIUS_SM}px; background-color:{T.SURFACE_LIGHT}; margin-top:-1px; }}
    QTabBar::tab {{ font-family:{T.FONT_FAMILY}; font-size:{T.FONT_SIZE_SM}px; font-weight:600; color:{T.TEXT_SECONDARY}; background-color:transparent; border:none; border-bottom:3px solid transparent; padding:10px {T.SPACE_LG}px; margin-right:4px; min-width:100px; min-height:20px; }}
    QTabBar::tab:selected {{ color:{T.INTERACTIVE}; border-bottom:3px solid {T.INTERACTIVE}; }}
    QTabBar::tab:hover {{ color:{T.INTERACTIVE_HOVER}; background-color:{T.INTERACTIVE_LIGHT}; }}
    QProgressBar {{ border:none; border-radius:{T.RADIUS_SM}px; background-color:{T.BORDER_LIGHT}; text-align:center; font-size:{T.FONT_SIZE_SM}px; color:{T.TEXT_PRIMARY}; min-height:24px; }}
    QProgressBar::chunk {{ background-color:{T.INTERACTIVE}; border-radius:{T.RADIUS_SM}px; }}
    QTreeWidget {{ font-family:{T.FONT_FAMILY}; font-size:{T.FONT_SIZE_SM}px; border:1px solid {T.BORDER_LIGHT}; border-radius:{T.RADIUS_SM}px; background-color:{T.SURFACE_LIGHT}; alternate-background-color:{T.SURFACE_ALT}; }}
    QTreeWidget::item {{ padding:4px 8px; min-height:28px; }}
    QTreeWidget::item:selected {{ background-color:{T.INTERACTIVE_LIGHT}; color:{T.TEXT_PRIMARY}; }}
    QHeaderView::section {{ font-family:{T.FONT_FAMILY}; font-size:{T.FONT_SIZE_SM}px; font-weight:600; color:{T.TEXT_PRIMARY}; background-color:{T.SURFACE_ALT}; border:none; border-bottom:2px solid {T.BORDER}; padding:6px 8px; }}
    QTextEdit {{ font-family:{T.FONT_FAMILY}; font-size:{T.FONT_SIZE_SM}px; color:{T.TEXT_PRIMARY}; background-color:{T.SURFACE_LIGHT}; border:1px solid {T.BORDER_LIGHT}; border-radius:{T.RADIUS_SM}px; padding:{T.SPACE_SM}px; }}
    QTextEdit QScrollBar:vertical {{ background:{T.SURFACE_ALT}; width:12px; margin:0px; border-radius:6px; }}
    QTextEdit QScrollBar::handle:vertical {{ background:{T.BORDER}; min-height:30px; border-radius:6px; }}
    QTextEdit QScrollBar::handle:vertical:hover {{ background:{T.TEXT_SECONDARY}; }}
    QTextEdit QScrollBar::add-line:vertical, QTextEdit QScrollBar::sub-line:vertical {{ height:0px; }}
    QFrame#headerFrame {{ background-color:{T.SURFACE_DARK}; border-radius:{T.RADIUS_SM}px; }}
    QFrame#divider {{ background-color:{T.DIVIDER}; max-height:1px; min-height:1px; }}
    """


class ValidationDialog(QDialog):
    """Main dialog — SICAR AD: Validate Environmental Dataset Structure."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Load i18n using the QGIS locale (auto-detected).
        self._i18n = I18n.from_qgis()
        self._locale = self._i18n.locale
        self.report = None
        self._layer_mapping = {}  # {expected: found}
        self._layer_comboboxes = {}  # {expected: QComboBox}
        self._pending_renames = {}  # {old_name: new_name}
        self.setMinimumSize(1000, 720)
        self.setStyleSheet(_govbr_stylesheet())
        self.setup_ui()

    # ------------------------------------------------------------------
    # i18n helpers (delegate to I18n instance)
    # ------------------------------------------------------------------

    def _t(self, key: str, **kw) -> str:
        return self._i18n.t(f"ui.{key}", **kw)

    def _change_language(self, locale: str):
        if locale == self._locale:
            return
        self._locale = locale
        self._i18n = I18n(locale)
        self._retranslate_ui()

    def _retranslate_ui(self):
        t = self._t
        self.setWindowTitle(t("window_title"))
        self._header_title_label.setText(t("header_title"))
        self._header_subtitle_label.setText(t("header_subtitle"))
        self._btn_language.setText(_LANGUAGE_LABELS.get(self._locale, "🌐"))
        self.tabs.setTabText(self.tabs.indexOf(self.tab_source), t("tab_source"))
        self.tabs.setTabText(self.tabs.indexOf(self.tab_rules), t("tab_rules"))
        idx_r = self.tabs.indexOf(self.tab_results)
        if idx_r >= 0: self.tabs.setTabText(idx_r, t("tab_results"))
        idx_l = self.tabs.indexOf(self.tab_log)
        if idx_l >= 0: self.tabs.setTabText(idx_l, t("tab_log"))
        self._file_hint_label.setText(t("file_hint"))
        self._btn_gpkg.setText(t("btn_select_gpkg"))
        self._btn_gdb.setText(t("btn_select_gdb"))
        self.file_input.setPlaceholderText(t("file_placeholder"))
        self._mapping_header_label.setText(t("lbl_layer_mapping"))
        self._btn_rename.setText(t("btn_rename_layers"))
        self._mapping_table.setHeaderLabels([t("col_expected"), t("col_found"), t("col_situation")])
        self.chk_layer_filter.setText(t("chk_layer_filter"))
        self.chk_detailed.setText(t("chk_detailed"))
        self.lbl_error_limit.setText(t("lbl_error_limit"))
        self.btn_validate.setText(t("btn_validate"))
        self.sub_tabs.setTabText(self.sub_tabs.indexOf(self.tab_format), t("subtab_format"))
        self.sub_tabs.setTabText(self.sub_tabs.indexOf(self.tab_conceptual), t("subtab_conceptual"))
        self.sub_tabs.setTabText(self.sub_tabs.indexOf(self.tab_domain), t("subtab_domain"))
        self._lbl_section_consistencies.setText(t("section_consistencies"))
        idx_tp = self.sub_tabs.indexOf(self.tab_topological)
        if idx_tp >= 0:
            self.sub_tabs.setTabText(idx_tp, t("subtab_topo_detail") if self.chk_detailed.isChecked() else t("subtab_topological"))
        self.tree_format.setHeaderLabels([t("col_check"), t("col_status"), t("col_details")])
        self.tree_conceptual.setHeaderLabels([t("col_layer"), t("col_check"), t("col_status"), t("col_details")])
        self.tree_domain.setHeaderLabels([t("col_layer"), t("col_check"), t("col_status"), t("col_details")])
        if self.tree_topological.columnCount() == 5:
            self.tree_topological.setHeaderLabels([t("col_layer"), t("col_check"), t("col_status"), t("col_details"), t("col_wkt")])
        else:
            self.tree_topological.setHeaderLabels([t("col_layer"), t("col_check"), t("col_status"), t("col_details")])
        self.btn_export_pdf.setText(t("btn_export_pdf"))
        self._rules_browser.setHtml(self._get_rules_html())
        if self.report is not None:
            self._fill_summary(self.report)

    def _show_language_menu(self):
        from qgis.PyQt.QtWidgets import QMenu
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background-color:{GovBRTokens.SURFACE_LIGHT}; border:1px solid {GovBRTokens.BORDER}; border-radius:{GovBRTokens.RADIUS_SM}px; font-family:{GovBRTokens.FONT_FAMILY}; font-size:{GovBRTokens.FONT_SIZE_SM}px; padding:4px 0; }}
            QMenu::item {{ padding:6px 20px; color:{GovBRTokens.TEXT_PRIMARY}; }}
            QMenu::item:selected {{ background-color:{GovBRTokens.INTERACTIVE_LIGHT}; color:{GovBRTokens.INTERACTIVE}; }}
            QMenu::item:checked {{ font-weight:600; color:{GovBRTokens.INTERACTIVE}; }}
        """)
        for loc in available_locales():
            label = _LANGUAGE_LABELS.get(loc, f"🌐 {loc}")
            meta = _i18n_load_catalogue(loc).get("_meta", {})
            display = f"{label}  —  {meta.get('language', loc)}"
            action = menu.addAction(display)
            action.setCheckable(True)
            action.setChecked(loc == self._locale)
            action.setData(loc)
        chosen = menu.exec_(self._btn_language.mapToGlobal(self._btn_language.rect().bottomLeft()))
        if chosen is not None:
            self._change_language(chosen.data())

    # ------------------------------------------------------------------
    # Engine output translation (delegates to I18n)
    # ------------------------------------------------------------------

    def _translate_status(self, status_value: str) -> str:
        return self._i18n.translate_status(status_value)

    def _translate_check_name(self, name: str) -> str:
        return self._i18n.translate_check_name(name)

    def _translate_detail(self, detail: str) -> str:
        return self._i18n.translate_detail(detail)

    def _localized_summary(self, report) -> str:
        # Exclude per-FID detail entries from counts
        rule_checks = [
            c for c in report.checks
            if not (c.name.startswith("Error in feature FID") or
                    c.name.startswith("Warning in feature FID"))
        ]
        total    = len(rule_checks)
        ok       = sum(1 for c in rule_checks if c.status == Status.CONFORMANT)
        non_conf = sum(1 for c in rule_checks if c.status == Status.NON_CONFORMANT)
        warnings = sum(1 for c in rule_checks if c.status == Status.WARNING)
        return self._i18n.localized_summary(total, ok, non_conf, warnings)


    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Header
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_outer = QHBoxLayout(header_frame)
        header_outer.setContentsMargins(16, 10, 16, 10)
        header_outer.setSpacing(8)

        header_text = QVBoxLayout()
        header_text.setSpacing(2)
        self._header_title_label = QLabel(self._t("header_title"))
        self._header_title_label.setObjectName("headerTitle")
        header_text.addWidget(self._header_title_label)
        self._header_subtitle_label = QLabel(self._t("header_subtitle"))
        self._header_subtitle_label.setObjectName("headerSubtitle")
        header_text.addWidget(self._header_subtitle_label)
        header_outer.addLayout(header_text, 1)

        self._btn_language = QPushButton(_LANGUAGE_LABELS.get(self._locale, "🌐"))
        self._btn_language.setObjectName("langBtn")
        self._btn_language.setCursor(_CURSOR_POINTING)
        self._btn_language.setFixedHeight(28)
        self._btn_language.setFixedWidth(64)
        self._btn_language.setStyleSheet(f"""
            QPushButton#langBtn {{ background-color:rgba(255,255,255,0.15); color:#FFFFFF; border:1px solid rgba(255,255,255,0.4); border-radius:{GovBRTokens.RADIUS_SM}px; font-size:{GovBRTokens.FONT_SIZE_SM}px; font-weight:600; padding:2px 8px; min-height:0px; }}
            QPushButton#langBtn:hover {{ background-color:rgba(255,255,255,0.28); }}
        """)
        self._btn_language.clicked.connect(self._show_language_menu)
        header_outer.addWidget(self._btn_language, 0)
        layout.addWidget(header_frame)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setSizePolicy(_SP_EXPANDING, _SP_EXPANDING)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.setElideMode(Qt.TextElideMode.ElideNone if hasattr(Qt, 'TextElideMode') else Qt.ElideNone)

        self.tab_source = QWidget()
        self._setup_tab_source()
        self.tabs.addTab(self.tab_source, self._t("tab_source"))

        self.tab_rules = QWidget()
        self._setup_tab_rules()
        self.tabs.addTab(self.tab_rules, self._t("tab_rules"))

        self.tab_results = QWidget()
        self._setup_tab_results()

        self.tab_log = QWidget()
        self._setup_tab_log()

        layout.addWidget(self.tabs)

        footer_divider = QFrame()
        footer_divider.setObjectName("divider")
        layout.addWidget(footer_divider)

    # ------------------------------------------------------------------
    # Tab: Source Dataset
    # ------------------------------------------------------------------

    def _setup_tab_source(self):
        layout = QVBoxLayout(self.tab_source)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._file_hint_label = QLabel(self._t("file_hint"))
        self._file_hint_label.setWordWrap(True)
        self._file_hint_label.setStyleSheet(f"color:{GovBRTokens.TEXT_SECONDARY}; font-size:{GovBRTokens.FONT_SIZE_SM}px;")
        layout.addWidget(self._file_hint_label)

        file_row = QHBoxLayout()
        file_row.setSpacing(8)
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText(self._t("file_placeholder"))
        self.file_input.setReadOnly(True)
        file_row.addWidget(self.file_input, 1)

        self._btn_gpkg = QPushButton(self._t("btn_select_gpkg"))
        self._btn_gpkg.setObjectName("secondaryBtn")
        self._btn_gpkg.setCursor(_CURSOR_POINTING)
        self._btn_gpkg.clicked.connect(self._browse_gpkg)
        file_row.addWidget(self._btn_gpkg)

        self._btn_gdb = QPushButton(self._t("btn_select_gdb"))
        self._btn_gdb.setObjectName("secondaryBtn")
        self._btn_gdb.setCursor(_CURSOR_POINTING)
        self._btn_gdb.clicked.connect(self._browse_gdb)
        file_row.addWidget(self._btn_gdb)
        layout.addLayout(file_row)

        # ── Divider between file selector and layer mapping ─────────────
        file_mapping_divider = QFrame()
        file_mapping_divider.setObjectName("divider")
        layout.addWidget(file_mapping_divider)

        # ── Layer Mapping Section ──────────────────────────────────────
        # Always visible for better UX - shows structure even before file selection
        self._mapping_frame = QFrame()
        self._mapping_frame.setVisible(True)  # Always visible
        mapping_layout = QVBoxLayout(self._mapping_frame)
        mapping_layout.setContentsMargins(0, 12, 0, 8)
        mapping_layout.setSpacing(8)

        # Header
        self._mapping_header_label = QLabel(self._t("lbl_layer_mapping"))
        self._mapping_header_label.setStyleSheet(f"font-weight:600; font-size:{GovBRTokens.FONT_SIZE_MD}px; color:{GovBRTokens.TEXT_PRIMARY};")
        mapping_layout.addWidget(self._mapping_header_label)

        # Summary
        self._mapping_summary_label = QLabel(self._t("lbl_mapping_summary").format(total=10, found=0, pending=0))
        self._mapping_summary_label.setStyleSheet(f"color:{GovBRTokens.TEXT_SECONDARY}; font-size:{GovBRTokens.FONT_SIZE_SM}px;")
        mapping_layout.addWidget(self._mapping_summary_label)

        # Table - starts with placeholder content
        self._mapping_table = QTreeWidget()
        self._mapping_table.setHeaderLabels([self._t("col_expected"), self._t("col_found"), self._t("col_situation")])
        self._mapping_table.setAlternatingRowColors(True)
        self._mapping_table.setMinimumHeight(180)
        self._mapping_table.setMaximumHeight(220)
        self._mapping_table.setColumnWidth(0, 220)
        self._mapping_table.setColumnWidth(1, 280)
        self._mapping_table.setColumnWidth(2, 180)
        
        # Add placeholder rows to show expected structure
        from .validator import EXPECTED_LAYERS
        for expected in EXPECTED_LAYERS:
            item = QTreeWidgetItem()
            item.setText(0, expected)
            item.setText(1, "—")
            item.setText(2, "")
            item.setForeground(0, QColor(GovBRTokens.TEXT_SECONDARY))
            item.setForeground(1, QColor(GovBRTokens.TEXT_SECONDARY))
            self._mapping_table.addTopLevelItem(item)
        
        mapping_layout.addWidget(self._mapping_table)

        # Rename button
        rename_btn_row = QHBoxLayout()
        self._btn_rename = QPushButton(self._t("btn_rename_layers"))
        self._btn_rename.setObjectName("secondaryBtn")
        self._btn_rename.setCursor(_CURSOR_POINTING)
        self._btn_rename.setEnabled(False)
        self._btn_rename.clicked.connect(self._rename_layers)
        rename_btn_row.addStretch()
        rename_btn_row.addWidget(self._btn_rename)
        mapping_layout.addLayout(rename_btn_row)

        layout.addWidget(self._mapping_frame)
        
        # ── Divider line before validation controls ────────────────────
        divider_frame = QFrame()
        divider_frame.setObjectName("divider")
        layout.addWidget(divider_frame)

        # ── Row: layer filter + detailed validation ──────────────────────
        layer_row = QHBoxLayout()
        layer_row.setContentsMargins(0, 4, 0, 4)
        layer_row.setSpacing(0)

        # — Left group: checkbox + combobox (tight spacing) —
        left_group = QHBoxLayout()
        left_group.setSpacing(4)
        left_group.setContentsMargins(0, 0, 0, 0)

        self.chk_layer_filter = QCheckBox(self._t("chk_layer_filter"))
        self.chk_layer_filter.setEnabled(False)
        self.chk_layer_filter.setStyleSheet("font-weight:600;")
        self.chk_layer_filter.stateChanged.connect(self._on_layer_filter_toggled)
        left_group.addWidget(self.chk_layer_filter)

        self.cmb_layer_filter = QComboBox()
        self.cmb_layer_filter.setEnabled(False)
        self.cmb_layer_filter.setMinimumWidth(220)
        self.cmb_layer_filter.addItem("")
        for ln in EXPECTED_LAYERS:
            self.cmb_layer_filter.addItem(ln)
        self.cmb_layer_filter.currentIndexChanged.connect(self._on_layer_combo_changed)
        left_group.addWidget(self.cmb_layer_filter)

        layer_row.addLayout(left_group)
        layer_row.addStretch(1)

        # — Right group: detailed + label + input —
        right_group = QHBoxLayout()
        right_group.setSpacing(8)
        right_group.setContentsMargins(0, 0, 0, 0)
        try:
            right_group.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        except AttributeError:
            right_group.setAlignment(Qt.AlignVCenter)

        self.chk_detailed = QCheckBox(self._t("chk_detailed"))
        self.chk_detailed.setEnabled(False)
        self.chk_detailed.setStyleSheet("font-weight:600;")
        self.chk_detailed.stateChanged.connect(self._on_detailed_toggled)
        right_group.addWidget(self.chk_detailed)

        self.lbl_error_limit = QLabel(self._t("lbl_error_limit"))
        self.lbl_error_limit.setEnabled(False)
        self.lbl_error_limit.setStyleSheet(f"font-weight:600; color:{GovBRTokens.TEXT_SECONDARY};")
        self.lbl_error_limit.setAlignment(_ALIGN_CENTER)
        right_group.addWidget(self.lbl_error_limit)

        self.txt_error_limit = QLineEdit()
        self.txt_error_limit.setText("10")
        self.txt_error_limit.setEnabled(False)
        self.txt_error_limit.setFixedWidth(36)
        self.txt_error_limit.setAlignment(_ALIGN_CENTER)
        self.txt_error_limit.setValidator(QIntValidator(1, 9999, self))
        self.txt_error_limit.setStyleSheet(
            f"border:1px solid {GovBRTokens.BORDER}; "
            f"border-radius:{GovBRTokens.RADIUS_SM}px; "
            f"padding:2px 4px; "
            f"font-size:{GovBRTokens.FONT_SIZE_SM}px; "
            f"min-height:0px;"
        )
        right_group.addWidget(self.txt_error_limit)

        layer_row.addLayout(right_group)
        layer_row.addStretch(1)

        layout.addLayout(layer_row)

        btn_row = QHBoxLayout()
        self.btn_validate = QPushButton(self._t("btn_validate"))
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
        layout = QVBoxLayout(self.tab_rules)
        layout.setContentsMargins(12, 12, 12, 12)
        self._rules_browser = QTextBrowser()
        self._rules_browser.setOpenExternalLinks(True)
        self._rules_browser.setSizePolicy(_SP_EXPANDING, _SP_EXPANDING)
        self._rules_browser.setHtml(self._get_rules_html())
        layout.addWidget(self._rules_browser)

    def _get_rules_html(self) -> str:
        T = GovBRTokens
        t = self._t
        tbl = f"border-collapse:collapse; width:100%; font-size:{T.FONT_SIZE_SM}px;"
        th  = f"padding:6px 10px; text-align:left; border-bottom:2px solid {T.BORDER};"
        td  = f"padding:6px 10px; border-bottom:1px solid {T.BORDER_LIGHT};"
        ref_html = self._get_references_html()
        return f"""
        <div style="font-family:{T.FONT_FAMILY}; color:{T.TEXT_PRIMARY}; font-size:{T.FONT_SIZE_SM}px; line-height:1.5;">
        <h2 style="color:{T.SURFACE_DARK}; font-weight:600; font-size:14px;">{t("rules_title")}</h2>
        <p>{t("rules_intro")}</p>
        <div style="background-color:{T.INFO_BG}; border-left:4px solid {T.INFO}; padding:12px 16px; border-radius:4px; margin:12px 0;">
            <b style="color:{T.INFO};">{t("rules_info_title")}</b><br>{t("rules_info_body")}
        </div>
        {ref_html}
        <hr style="border:none; border-top:1px solid {T.DIVIDER}; margin:12px 0;">
        <h3 style="color:{T.INTERACTIVE}; font-weight:600; font-size:13px;">{t("sec_format")}</h3>
        <table style="{tbl}"><tr style="background:{T.SURFACE_ALT};"><th style="{th}">{t("col_rule")}</th><th style="{th}">{t("col_description")}</th></tr>
        <tr><td style="{td}">{t("rule_dataset_format")}</td><td style="{td}">{t("rule_dataset_format_desc")}</td></tr>
        <tr><td style="{td}">{t("rule_dataset_readability")}</td><td style="{td}">{t("rule_dataset_readability_desc")}</td></tr></table>
        <h3 style="color:{T.INTERACTIVE}; font-weight:600; font-size:13px; margin-top:14px;">{t("sec_conceptual")}</h3>
        <table style="{tbl}"><tr style="background:{T.SURFACE_ALT};"><th style="{th}">{t("col_rule")}</th><th style="{th}">{t("col_description")}</th></tr>
        <tr><td style="{td}">{t("rule_layer_names")}</td><td style="{td}">APP, AREA_ANTROPIZADA, AREA_CONSOLIDADA, HIDROGRAFIA, VEGETACAO_2008, VEGETACAO_ATUAL, SERVIDAO, RELEVO, USO_RESTRITO, APP_ESPECIAL</td></tr>
        <tr><td style="{td}">{t("rule_records")}</td><td style="{td}">{t("rule_records_desc")}</td></tr>
        <tr><td style="{td}">{t("rule_classe_attr")}</td><td style="{td}">{t("rule_classe_attr_desc")}</td></tr>
        <tr><td style="{td}">{t("rule_crs")}</td><td style="{td}">{t("rule_crs_desc")}</td></tr></table>
        <h3 style="color:{T.INTERACTIVE}; font-weight:600; font-size:13px; margin-top:14px;">{t("sec_domain")}</h3>
        <table style="{tbl}"><tr style="background:{T.SURFACE_ALT};"><th style="{th}">{t("col_rule")}</th><th style="{th}">{t("col_description")}</th></tr>
        <tr><td style="{td}">{t("rule_numeric_type")}</td><td style="{td}">{t("rule_numeric_type_desc")}</td></tr>
        <tr><td style="{td}">{t("rule_null_values")}</td><td style="{td}">{t("rule_null_values_desc")}</td></tr>
        <tr><td style="{td}">{t("rule_domain")}</td><td style="{td}">{t("rule_domain_desc")}</td></tr></table>
        <h3 style="color:{T.INTERACTIVE}; font-weight:600; font-size:13px; margin-top:14px;">{t("sec_topological")}</h3>
        <table style="{tbl}"><tr style="background:{T.SURFACE_ALT};"><th style="{th}">{t("col_rule")}</th><th style="{th}">{t("col_description")}</th></tr>
        <tr><td style="{td}">{t("rule_null_empty_geom")}</td><td style="{td}">{t("rule_null_empty_geom_desc")}</td></tr>
        <tr><td style="{td}">{t("rule_topo_errors")}</td><td style="{td}">{t("rule_topo_errors_desc")}</td></tr>
        <tr><td style="{td}">{t("rule_2d_geom")}</td><td style="{td}">{t("rule_2d_geom_desc")}</td></tr></table>
        </div>"""

    def _get_references_html(self) -> str:
        if not REFERENCES:
            return ""
        T = GovBRTokens
        ref = REFERENCES[0]
        # Use localised title when available (e.g. "title_pt_BR"), fall back to "title"
        locale_key = f"title_{self._locale}"
        title = ref.get(locale_key) or ref.get("title", "")
        url   = ref.get("url", "")
        if not title or not url:
            return ""
        intro = self._t("rules_ref_intro")
        return (f"<div style='background-color:{T.SURFACE_ALT}; border:1px solid {T.BORDER_LIGHT}; "
                f"padding:12px 16px; border-radius:4px; margin:12px 0;'>"
                f"{intro} \"<a href='{url}' style='color:{T.INTERACTIVE}; font-weight:600;'>{title}</a>\"."
                f"</div>")

    # ------------------------------------------------------------------
    # Tab: Results
    # ------------------------------------------------------------------

    def _setup_tab_results(self):
        layout = QVBoxLayout(self.tab_results)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.summary_text = QTextBrowser()
        self.summary_text.setOpenExternalLinks(False)
        self.summary_text.setMaximumHeight(220)
        self.summary_text.setSizePolicy(_SP_EXPANDING, QSizePolicy.Maximum if hasattr(QSizePolicy, 'Maximum') else QSizePolicy.Policy.Maximum)
        layout.addWidget(self.summary_text)

        # ── Section divider: "Consistências / Consistencies" ─────────────
        # A horizontal rule with the section label on the left, visually
        # grouping the sub-tabs under a single "Consistencies" heading so
        # the word "Consistency" does not need to repeat on every tab.
        section_row = QHBoxLayout()
        section_row.setContentsMargins(0, 4, 0, 0)
        section_row.setSpacing(6)

        self._lbl_section_consistencies = QLabel(self._t("section_consistencies"))
        self._lbl_section_consistencies.setStyleSheet(
            f"font-family:{GovBRTokens.FONT_FAMILY}; "
            f"font-size:{GovBRTokens.FONT_SIZE_SM}px; "
            f"font-weight:600; "
            f"color:{GovBRTokens.TEXT_SECONDARY};"
        )
        section_row.addWidget(self._lbl_section_consistencies)

        # Horizontal line to the right of the label (soft grey, 1px)
        line = QFrame()
        line.setFrameShape(QFrame.HLine if hasattr(QFrame, 'HLine') else QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Plain if hasattr(QFrame, 'Plain') else QFrame.Shadow.Plain)
        line.setStyleSheet(
            f"color:{GovBRTokens.BORDER_LIGHT}; "
            f"background-color:{GovBRTokens.BORDER_LIGHT}; "
            f"max-height:1px; min-height:1px;"
        )
        line.setSizePolicy(_SP_EXPANDING,
                           QSizePolicy.Fixed if hasattr(QSizePolicy, 'Fixed') else QSizePolicy.Policy.Fixed)
        section_row.addWidget(line)

        layout.addLayout(section_row)

        self.sub_tabs = QTabWidget()
        self.sub_tabs.setSizePolicy(_SP_EXPANDING, _SP_EXPANDING)

        t = self._t
        self.tab_format = QWidget()
        self.tree_format = self._make_tree(self.tab_format, [t("col_check"), t("col_status"), t("col_details")])
        self.sub_tabs.addTab(self.tab_format, t("subtab_format"))

        self.tab_conceptual = QWidget()
        self.tree_conceptual = self._make_tree(self.tab_conceptual, [t("col_layer"), t("col_check"), t("col_status"), t("col_details")])
        self.sub_tabs.addTab(self.tab_conceptual, t("subtab_conceptual"))

        self.tab_domain = QWidget()
        self.tree_domain = self._make_tree(self.tab_domain, [t("col_layer"), t("col_check"), t("col_status"), t("col_details")])
        self.sub_tabs.addTab(self.tab_domain, t("subtab_domain"))

        self.tab_topological = QWidget()
        self.tree_topological = self._make_tree(self.tab_topological, [t("col_layer"), t("col_check"), t("col_status"), t("col_details")])
        self.sub_tabs.addTab(self.tab_topological, t("subtab_topological"))

        layout.addWidget(self.sub_tabs)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()
        self.btn_export_pdf = QPushButton(t("btn_export_pdf"))
        self.btn_export_pdf.setObjectName("secondaryBtn")
        self.btn_export_pdf.setCursor(_CURSOR_POINTING)
        self.btn_export_pdf.clicked.connect(self.export_pdf)
        btn_row.addWidget(self.btn_export_pdf)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _make_tree(self, parent: QWidget, headers: list) -> QTreeWidget:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(4, 4, 4, 4)
        tree = QTreeWidget()
        tree.setHeaderLabels(headers)
        tree.setColumnWidth(0, 200)
        if len(headers) > 4:
            tree.setColumnWidth(1, 180); tree.setColumnWidth(2, 140)
            tree.setColumnWidth(3, 300); tree.setColumnWidth(4, 400)
        elif len(headers) > 3:
            tree.setColumnWidth(1, 180); tree.setColumnWidth(2, 140)
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
        layout = QVBoxLayout(self.tab_log)
        layout.setContentsMargins(12, 12, 12, 12)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn if hasattr(Qt, 'ScrollBarPolicy') else Qt.ScrollBarAlwaysOn)
        self.log_text.setStyleSheet(f"font-family:'Consolas','Courier New',monospace; font-size:{GovBRTokens.FONT_SIZE_XS}px; background-color:{GovBRTokens.SURFACE_LIGHT}; color:{GovBRTokens.TEXT_PRIMARY}; border-radius:{GovBRTokens.RADIUS_SM}px; padding:{GovBRTokens.SPACE_SM}px;")
        self.log_text.setSizePolicy(_SP_EXPANDING, _SP_EXPANDING)
        layout.addWidget(self.log_text)


    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _browse_gpkg(self):
        filepath, _ = QFileDialog.getOpenFileName(self, self._t("dlg_select_gpkg"), "", self._t("dlg_gpkg_filter"))
        if filepath:
            self.file_input.setText(filepath)
            self.btn_validate.setEnabled(True)
            self.chk_layer_filter.setEnabled(True)
            self._hide_results()
            self._load_layer_mapping(Path(filepath))
        # If cancelled, no action needed - table remains in current state

    def _browse_gdb(self):
        dirpath = QFileDialog.getExistingDirectory(self, self._t("dlg_select_gdb"), "", _SHOW_DIRS_ONLY)
        if dirpath:
            if dirpath.lower().endswith(".gdb"):
                self.file_input.setText(dirpath)
                self.btn_validate.setEnabled(True)
                self.chk_layer_filter.setEnabled(True)
                self._hide_results()
                self._load_layer_mapping(Path(dirpath))
            else:
                QMessageBox.warning(self, self._t("err_invalid_format"), self._t("err_invalid_format_msg"))
        # If cancelled, no action needed - table remains in current state

    def _on_layer_filter_toggled(self, state):
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
        checked = int(state) == int(_QT_CHECKED)
        if checked:
            if not self.chk_layer_filter.isChecked() or not self.cmb_layer_filter.currentText().strip():
                self.chk_detailed.setChecked(False)
                QMessageBox.warning(self, self._t("warn_detailed"), self._t("warn_detailed_msg"))
                return
        self.lbl_error_limit.setEnabled(checked)
        self.txt_error_limit.setEnabled(checked)

    def _update_detailed_checkbox_state(self):
        can = self.chk_layer_filter.isChecked() and self.cmb_layer_filter.currentText().strip() != ""
        self.chk_detailed.setEnabled(can)
        if not can:
            self.chk_detailed.setChecked(False)

    def _on_layer_combo_changed(self, index):
        self._update_detailed_checkbox_state()

    def _hide_results(self):
        for tab in (self.tab_results, self.tab_log):
            idx = self.tabs.indexOf(tab)
            if idx >= 0:
                self.tabs.removeTab(idx)

    def _show_results(self):
        if self.tabs.indexOf(self.tab_results) < 0:
            self.tabs.addTab(self.tab_results, self._t("tab_results"))
        if self.tabs.indexOf(self.tab_log) < 0:
            self.tabs.addTab(self.tab_log, self._t("tab_log"))
        self.tabs.setCurrentWidget(self.tab_results)

    def _log_diagnostics(self, base_path: str):
        import os, sys, platform
        T = GovBRTokens
        t = self._t
        hs = f"color:{T.INTERACTIVE}; font-weight:600;"
        ls = f"color:{T.TEXT_SECONDARY};"
        vs = f"color:{T.TEXT_PRIMARY};"
        lines = [f"<span style='{hs}'>{t('diag_title')}</span>"]
        lines.append(f"<br><span style='{hs}'>{t('diag_input')}</span>")
        try:
            p = Path(base_path)
            if p.is_file():
                sz = p.stat().st_size
                s = f"{sz/1024:.1f} KB" if sz < 1048576 else f"{sz/1048576:.1f} MB"
                lines.append(f"  <span style='{ls}'>{t('diag_file')}:</span> <span style='{vs}'>{p.name} ({s})</span>")
            elif p.is_dir():
                tot = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                lines.append(f"  <span style='{ls}'>{t('diag_dir')}:</span> <span style='{vs}'>{p.name} ({tot/1048576:.1f} MB)</span>")
            else:
                lines.append(f"  <span style='{ls}'>{t('diag_path')}:</span> <span style='{vs}'>{base_path}</span>")
        except Exception:
            lines.append(f"  <span style='{ls}'>{t('diag_path')}:</span> <span style='{vs}'>{base_path}</span>")
        lines.append(f"<br><span style='{hs}'>{t('diag_software')}</span>")
        try:
            from qgis.core import Qgis
            qv = Qgis.QGIS_VERSION
        except Exception:
            qv = t("diag_na")
        lines.append(f"  <span style='{ls}'>QGIS:</span> <span style='{vs}'>{qv}</span>")
        lines.append(f"  <span style='{ls}'>Python:</span> <span style='{vs}'>{sys.version.split()[0]}</span>")
        libs = {}
        for lib in ("geopandas", "pyogrio", "shapely"):
            try:
                m = __import__(lib); libs[lib] = getattr(m, "__version__", "?")
            except ImportError:
                libs[lib] = t("diag_na")
        lines.append(f"  <span style='{ls}'>{t('diag_libs')}:</span> <span style='{vs}'>{' | '.join(f'{k} {v}' for k,v in libs.items())}</span>")
        lines.append(f"<br><span style='{hs}'>{t('diag_system')}</span>")
        lines.append(f"  <span style='{ls}'>{t('diag_os')}:</span> <span style='{vs}'>{platform.system()} {platform.release()}</span>")
        lines.append(f"  <span style='{ls}'>{t('diag_encoding')}:</span> <span style='{vs}'>{sys.getfilesystemencoding()}</span>")
        lines.append(f"<br><span style='{hs}'>{t('diag_hardware')}</span>")
        lines.append(f"  <span style='{ls}'>{t('diag_cpu')}:</span> <span style='{vs}'>{self._get_cpu_name()} ({os.cpu_count() or 0} {t('diag_cores')})</span>")
        lines.append(f"  <span style='{ls}'>{t('diag_ram')}:</span> <span style='{vs}'>{self._get_ram_info()}</span>")
        lines.append(f"<br><span style='{hs}'>{t('diag_sep')}</span>")
        lines.append("")
        self.log_text.setHtml("<br>".join(lines))

    def _get_cpu_name(self) -> str:
        import platform
        if platform.system() == "Windows":
            try:
                import winreg
                k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
                n, _ = winreg.QueryValueEx(k, "ProcessorNameString"); winreg.CloseKey(k); return n.strip()
            except Exception: pass
        if platform.system() == "Linux":
            try:
                with open("/proc/cpuinfo") as f:
                    for l in f:
                        if l.startswith("model name"): return l.split(":", 1)[1].strip()
            except Exception: pass
        return self._t("diag_na")

    def _get_ram_info(self) -> str:
        import platform
        t = self._t
        try:
            import psutil; m = psutil.virtual_memory()
            return f"{m.total/1073741824:.1f} GB {t('diag_total')}, {m.available/1073741824:.1f} GB {t('diag_available')} ({m.percent:.0f}% {t('diag_in_use')})"
        except ImportError: pass
        if platform.system() == "Windows":
            try:
                import ctypes
                class MS(ctypes.Structure):
                    _fields_=[("dwLength",ctypes.c_ulong),("dwMemoryLoad",ctypes.c_ulong),("ullTotalPhys",ctypes.c_ulonglong),("ullAvailPhys",ctypes.c_ulonglong),("ullTotalPageFile",ctypes.c_ulonglong),("ullAvailPageFile",ctypes.c_ulonglong),("ullTotalVirtual",ctypes.c_ulonglong),("ullAvailVirtual",ctypes.c_ulonglong),("ullAvailExtendedVirtual",ctypes.c_ulonglong)]
                s = MS(); s.dwLength = ctypes.sizeof(s); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
                return f"{s.ullTotalPhys/1073741824:.1f} GB {t('diag_total')}, {s.ullAvailPhys/1073741824:.1f} GB {t('diag_available')} ({s.dwMemoryLoad}% {t('diag_in_use')})"
            except Exception: pass
        return t("diag_na")

    # ------------------------------------------------------------------
    # Layer Mapping Functions
    # ------------------------------------------------------------------

    def _load_layer_mapping(self, base_path: Path):
        """Loads and displays the layer mapping table."""
        from .validator import get_layer_mapping, list_layers, EXPECTED_LAYERS
        
        try:
            # Get the mapping
            mapping = get_layer_mapping(base_path)
            self._layer_mapping = mapping
            
            # Get all existing layers
            existing_layers = list_layers(base_path)
            
            # Clear the table
            self._mapping_table.clear()
            self._layer_comboboxes.clear()
            
            # Count statistics
            found_count = sum(1 for v in mapping.values() if v is not None)
            pending_count = len(mapping) - found_count
            
            # Update summary
            self._mapping_summary_label.setText(
                self._t("lbl_mapping_summary").format(
                    total=len(mapping),
                    found=found_count,
                    pending=pending_count
                )
            )
            self._mapping_summary_label.setStyleSheet(
                f"color:{GovBRTokens.TEXT_PRIMARY}; font-size:{GovBRTokens.FONT_SIZE_SM}px; font-weight:600;"
            )
            
            # Populate table
            for expected in EXPECTED_LAYERS:
                found = mapping.get(expected)
                item = QTreeWidgetItem()
                item.setText(0, expected)
                
                if found is not None:
                    # Coincident layer - locked
                    item.setText(1, found)
                    item.setText(2, self._t("sit_coincident"))
                    item.setForeground(2, QColor(GovBRTokens.SUCCESS))
                    # Disable editing
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable if hasattr(Qt, 'ItemFlag') else item.flags() & ~Qt.ItemIsEditable)
                else:
                    # Not found - add combobox
                    item.setText(1, "")
                    item.setText(2, self._t("sit_not_found"))
                    item.setForeground(2, QColor(GovBRTokens.ERROR))
                    
                    # Create combobox with available layers
                    combo = QComboBox()
                    combo.addItem(self._t("select_layer"), "")
                    
                    # Add layers that are not already mapped
                    used_layers = [v for v in mapping.values() if v is not None]
                    for layer in existing_layers:
                        if layer not in used_layers and layer.upper() not in [e.upper() for e in EXPECTED_LAYERS]:
                            combo.addItem(layer, layer)
                    
                    combo.currentIndexChanged.connect(lambda idx, exp=expected: self._on_mapping_changed(exp, idx))
                    self._layer_comboboxes[expected] = combo
                    
                self._mapping_table.addTopLevelItem(item)
                
                # Set combobox if applicable
                if found is None and expected in self._layer_comboboxes:
                    self._mapping_table.setItemWidget(item, 1, self._layer_comboboxes[expected])
            
            self._update_rename_button()
            
        except Exception as e:
            print(f"Error loading layer mapping: {e}")
            # Reset to placeholder state
            self._reset_mapping_table()
    
    def _reset_mapping_table(self):
        """Resets the mapping table to placeholder state."""
        from .validator import EXPECTED_LAYERS
        
        self._mapping_table.clear()
        self._layer_comboboxes.clear()
        self._layer_mapping.clear()
        self._pending_renames.clear()
        
        self._mapping_summary_label.setText(
            self._t("lbl_mapping_summary").format(total=len(EXPECTED_LAYERS), found=0, pending=0)
        )
        self._mapping_summary_label.setStyleSheet(
            f"color:{GovBRTokens.TEXT_SECONDARY}; font-size:{GovBRTokens.FONT_SIZE_SM}px;"
        )
        
        # Add placeholder rows
        for expected in EXPECTED_LAYERS:
            item = QTreeWidgetItem()
            item.setText(0, expected)
            item.setText(1, "—")
            item.setText(2, "")
            item.setForeground(0, QColor(GovBRTokens.TEXT_SECONDARY))
            item.setForeground(1, QColor(GovBRTokens.TEXT_SECONDARY))
            self._mapping_table.addTopLevelItem(item)
        
        self._btn_rename.setEnabled(False)
    
    def _on_mapping_changed(self, expected_layer: str, combo_index: int):
        """Called when user selects a layer in the combobox."""
        combo = self._layer_comboboxes.get(expected_layer)
        if combo is None:
            return
        
        selected = combo.itemData(combo_index)
        
        # Update mapping
        if selected:
            self._layer_mapping[expected_layer] = selected
            self._pending_renames[selected] = expected_layer
            
            # Update situation column
            for i in range(self._mapping_table.topLevelItemCount()):
                item = self._mapping_table.topLevelItem(i)
                if item.text(0) == expected_layer:
                    item.setText(2, self._t("sit_rename"))
                    item.setForeground(2, QColor(GovBRTokens.WARNING))
                    break
            
            # Update other comboboxes to remove this layer from options
            self._update_combobox_options()
        else:
            # Deselected
            if expected_layer in self._layer_mapping:
                old_selected = self._layer_mapping[expected_layer]
                if old_selected in self._pending_renames:
                    del self._pending_renames[old_selected]
                self._layer_mapping[expected_layer] = None
                
            # Update situation column
            for i in range(self._mapping_table.topLevelItemCount()):
                item = self._mapping_table.topLevelItem(i)
                if item.text(0) == expected_layer:
                    item.setText(2, self._t("sit_not_found"))
                    item.setForeground(2, QColor(GovBRTokens.ERROR))
                    break
            
            self._update_combobox_options()
        
        self._update_rename_button()
    
    def _update_combobox_options(self):
        """Updates all comboboxes to reflect currently selected layers."""
        from .validator import list_layers, EXPECTED_LAYERS
        
        base_path = self.file_input.text()
        if not base_path:
            return
        
        try:
            existing_layers = list_layers(Path(base_path))
            
            # Get all currently selected layers
            selected_layers = list(self._pending_renames.keys())
            coincident_layers = [v for k, v in self._layer_mapping.items() if v is not None and k not in self._pending_renames.values()]
            used_layers = selected_layers + coincident_layers
            
            # Update each combobox
            for expected, combo in self._layer_comboboxes.items():
                current_selection = combo.itemData(combo.currentIndex())
                combo.blockSignals(True)
                combo.clear()
                combo.addItem(self._t("select_layer"), "")
                
                # Add available layers
                for layer in existing_layers:
                    if layer not in used_layers or layer == current_selection:
                        if layer.upper() not in [e.upper() for e in EXPECTED_LAYERS]:
                            combo.addItem(layer, layer)
                
                # Restore selection
                if current_selection:
                    index = combo.findData(current_selection)
                    if index >= 0:
                        combo.setCurrentIndex(index)
                
                combo.blockSignals(False)
                
        except Exception as e:
            print(f"Error updating combobox options: {e}")
    
    def _update_rename_button(self):
        """Enables/disables the rename button based on pending renames."""
        self._btn_rename.setEnabled(len(self._pending_renames) > 0)
    
    def _rename_layers(self):
        """Renames the selected layers in the dataset."""
        from .validator import rename_layer_in_dataset, check_gdal_version_for_gdb_rename
        
        base_path = Path(self.file_input.text())
        if not base_path:
            return
        
        # Check GDAL version for .gdb
        if base_path.suffix.lower() == ".gdb":
            supported, version = check_gdal_version_for_gdb_rename()
            if not supported:
                QMessageBox.critical(
                    self,
                    self._t("err_gdb_version"),
                    self._t("err_gdb_version_msg").format(version=version)
                )
                return
        
        # Perform renames
        renamed_layers = []
        errors = []
        
        for old_name, new_name in self._pending_renames.items():
            success, message = rename_layer_in_dataset(base_path, old_name, new_name)
            if success:
                renamed_layers.append(f"{old_name} → {new_name}")
            else:
                errors.append(f"{old_name}: {message}")
        
        if errors:
            QMessageBox.critical(
                self,
                self._t("err_rename_title"),
                self._t("err_rename_msg").format(e="\n".join(errors))
            )
        elif renamed_layers:
            QMessageBox.information(
                self,
                self._t("success_rename"),
                self._t("success_rename_msg").format(layers="\n".join(renamed_layers))
            )
            # Reload mapping
            self._pending_renames.clear()
            self._load_layer_mapping(base_path)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def run_validation(self):
        import time
        base_path = self.file_input.text()
        if not base_path:
            return
        
        # Check for missing layers that haven't been mapped
        from .validator import EXPECTED_LAYERS
        missing_layers = []
        for expected in EXPECTED_LAYERS:
            found = self._layer_mapping.get(expected)
            if found is None and expected not in self._pending_renames.values():
                missing_layers.append(expected)
        
        if missing_layers:
            reply = QMessageBox.question(
                self,
                self._t("warn_missing_layers"),
                self._t("warn_missing_layers_msg"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No if hasattr(QMessageBox, 'StandardButton') else QMessageBox.Yes | QMessageBox.No,
                QMessageBox.StandardButton.No if hasattr(QMessageBox, 'StandardButton') else QMessageBox.No
            )
            if reply != (QMessageBox.StandardButton.Yes if hasattr(QMessageBox, 'StandardButton') else QMessageBox.Yes):
                return
        
        layer_filter = None
        if self.chk_layer_filter.isChecked():
            layer_filter = self.cmb_layer_filter.currentText().strip()
            if not layer_filter:
                QMessageBox.warning(self, self._t("err_no_layer"), self._t("err_no_layer_msg"))
                return
        self._clear_results()
        if self.tabs.indexOf(self.tab_log) < 0:
            self.tabs.addTab(self.tab_log, self._t("tab_log"))
        detailed = self.chk_detailed.isChecked()
        error_limit = None
        if detailed:
            txt = self.txt_error_limit.text().strip()
            if not txt:
                # Ask the user: proceed without a limit (slow) or cancel?
                msg = QMessageBox(self)
                msg.setWindowTitle(self._t("warn_no_limit"))
                msg.setText(self._t("warn_no_limit_msg"))
                msg.setIcon(QMessageBox.Warning if hasattr(QMessageBox, 'Warning') else QMessageBox.Icon.Warning)
                btn_ok     = msg.addButton("OK",     QMessageBox.AcceptRole if hasattr(QMessageBox, 'AcceptRole') else QMessageBox.ButtonRole.AcceptRole)
                btn_cancel = msg.addButton(self._t("btn_cancel"),
                                           QMessageBox.RejectRole if hasattr(QMessageBox, 'RejectRole') else QMessageBox.ButtonRole.RejectRole)
                msg.setDefaultButton(btn_cancel)
                msg.exec_()
                if msg.clickedButton() == btn_cancel:
                    return   # user chose to cancel — do not start validation
                # user chose OK — proceed without limit (error_limit stays None)
            else:
                error_limit = int(txt)
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
                progress_messages=self._i18n.get_progress_messages(),
            )
        except Exception as e:
            self.progress_bar.setVisible(False)
            self.progress_label.setVisible(False)
            self.btn_validate.setEnabled(True)
            QMessageBox.critical(self, self._t("err_validation"), self._t("err_validation_msg", e=e))
            return
        elapsed = time.time() - t0
        self.log_text.append(
            f"\n<span style='color:{GovBRTokens.SUCCESS}; font-weight:600;'>{self._t('log_completed')}</span> "
            f"{self._i18n.t('ui.log_total_time', t=elapsed)}"
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
            self.log_text.append(f"<span style='color:{GovBRTokens.INTERACTIVE};'>[{ts}]</span> <span style='color:{GovBRTokens.TEXT_PRIMARY};'>{message}</span>")
        QCoreApplication.processEvents()

    def _clear_results(self):
        self.tree_format.clear(); self.tree_conceptual.clear()
        self.tree_domain.clear(); self.tree_topological.clear()
        self.summary_text.clear(); self.log_text.clear()

    def _display_report(self, report: ValidationReport):
        t = self._t
        self._fill_tree(self.tree_format, report.format_checks, False)
        self._fill_tree(self.tree_conceptual, report.conceptual_checks, True)
        self._fill_tree(self.tree_domain, report.domain_checks, True)
        if self.chk_detailed.isChecked():
            self.tree_topological.clear()
            self.tree_topological.setColumnCount(5)
            self.tree_topological.setHeaderLabels([t("col_layer"), t("col_check"), t("col_status"), t("col_details"), t("col_wkt")])
            self.tree_topological.setColumnWidth(3, 300); self.tree_topological.setColumnWidth(4, 400)
            self._fill_tree_detailed(self.tree_topological, report.topological_checks)
            idx = self.sub_tabs.indexOf(self.tab_topological)
            if idx >= 0: self.sub_tabs.setTabText(idx, t("subtab_topo_detail"))
            self.sub_tabs.setCurrentWidget(self.tab_topological)
        else:
            self.tree_topological.clear()
            self.tree_topological.setColumnCount(4)
            self.tree_topological.setHeaderLabels([t("col_layer"), t("col_check"), t("col_status"), t("col_details")])
            self._fill_tree(self.tree_topological, report.topological_checks, True)
            idx = self.sub_tabs.indexOf(self.tab_topological)
            if idx >= 0: self.sub_tabs.setTabText(idx, t("subtab_topological"))
        self._fill_summary(report)

        # Show a warning dialog for each layer missing a geometry column.
        # The validator already registered these as NON_CONFORMANT checks so
        # they appear in the results grid — the message box gives immediate
        # visibility to the user before they look at the grid.
        no_geom_checks = [
            c for c in report.checks
            if c.name == "Geometry column missing"
        ]
        for chk in no_geom_checks:
            QMessageBox.warning(
                self,
                t("warn_no_geometry"),
                self._i18n.t("ui.warn_no_geometry_msg", layer=chk.layer),
            )

    def _fill_tree(self, tree: QTreeWidget, checks: list[CheckResult], with_layer: bool):
        tree.clear()
        for check in checks:
            item = QTreeWidgetItem()
            tn = self._translate_check_name(check.name)
            ts = self._translate_status(check.status.value)
            td = self._translate_detail(check.details)
            if with_layer:
                item.setText(0, check.layer); item.setText(1, tn); item.setText(2, ts); item.setText(3, td); scol = 2
            else:
                item.setText(0, tn); item.setText(1, ts); item.setText(2, td); scol = 1
            color = QColor(GovBRTokens.SUCCESS if check.status == Status.CONFORMANT else GovBRTokens.WARNING_TEXT if check.status == Status.WARNING else GovBRTokens.ERROR)
            item.setForeground(scol, color)
            tree.addTopLevelItem(item)
        for i in range(tree.columnCount()):
            tree.resizeColumnToContents(i)

    def _fill_tree_detailed(self, tree: QTreeWidget, checks: list[CheckResult]):
        tree.clear()
        for check in checks:
            item = QTreeWidgetItem()
            item.setText(0, check.layer)
            item.setText(1, self._translate_check_name(check.name))
            item.setText(2, self._translate_status(check.status.value))
            item.setText(3, self._translate_detail(check.details))
            item.setText(4, check.wkt if check.wkt else "")
            color = QColor(GovBRTokens.SUCCESS if check.status == Status.CONFORMANT else GovBRTokens.WARNING_TEXT if check.status == Status.WARNING else GovBRTokens.ERROR)
            item.setForeground(2, color)
            tree.addTopLevelItem(item)
        for i in range(tree.columnCount()):
            tree.resizeColumnToContents(i)


    def _fill_summary(self, report: ValidationReport):
        from .validator import list_layers, EXPECTED_LAYERS
        T = GovBRTokens
        t = self._t
        html = [f"<div style='font-family:{T.FONT_FAMILY}; color:{T.TEXT_PRIMARY}; font-size:{T.FONT_SIZE_SM}px; line-height:1.5;'>"]

        if report.passed and not report.has_warnings:
            bg, bdr, icon, text, clr = T.SUCCESS_BG, T.SUCCESS, "✓", t("status_conf"), T.SUCCESS
        elif report.passed and report.has_warnings:
            bg, bdr, icon, text, clr = T.WARNING_BG, T.WARNING_TEXT, "⚠", t("status_warn"), T.WARNING_TEXT
        else:
            bg, bdr, icon, text, clr = T.ERROR_BG, T.ERROR, "✗", t("status_nonconf"), T.ERROR

        html.append(f"<div style='background:{bg}; border-left:4px solid {bdr}; padding:10px 14px; border-radius:4px; margin-bottom:10px;'>"
                    f"<span style='font-size:16px; font-weight:700; color:{clr};'>{icon} {text}</span><br>"
                    f"<span style='font-size:11px; color:{T.TEXT_SECONDARY};'>{self._localized_summary(report)}</span></div>")

        src = report.file_path
        if getattr(self, '_current_layer_filter', None):
            src += f" — layer <b style='text-transform:uppercase;'>{self._current_layer_filter.upper()}</b>"
        html.append(f"<p style='font-size:11px; color:{T.TEXT_SECONDARY};'><b>{t('lbl_source')}:</b> {src}</p>")

        cat_map = {
            "Format Consistency":      t("cat_format"),
            "Conceptual Consistency":  t("cat_conceptual"),
            "Domain Consistency":      t("cat_domain"),
            "Topological Consistency": t("cat_topological"),
        }
        html.append(f"<table style='border-collapse:collapse; width:100%; font-size:{T.FONT_SIZE_SM}px; margin-top:6px;'>"
                    f"<tr style='background:{T.SURFACE_ALT};'>"
                    f"<th style='padding:6px 10px; text-align:left; border-bottom:2px solid {T.BORDER};'>Category</th>"
                    f"<th style='padding:6px 10px; text-align:left; border-bottom:2px solid {T.BORDER};'>Status</th>"
                    f"<th style='padding:6px 10px; text-align:left; border-bottom:2px solid {T.BORDER};'>{t('pdf_result')}</th></tr>")
        for cat, info in report.summary_by_category().items():
            cat_label = cat_map.get(cat, cat)
            if info["status"] == Status.CONFORMANT:
                st = f"<span style='color:{T.SUCCESS}; font-weight:600;'>{t('st_conformant')}</span>"; rbg = ""
            elif info["status"] == Status.WARNING:
                st = f"<span style='color:{T.WARNING_TEXT}; font-weight:600;'>{t('st_warning')}</span>"; rbg = f" style='background:{T.WARNING_BG};'"
            else:
                st = f"<span style='color:{T.ERROR}; font-weight:600;'>{t('st_nonconf')}</span>"; rbg = f" style='background:{T.ERROR_BG};'"
            html.append(f"<tr{rbg}><td style='padding:6px 10px; border-bottom:1px solid {T.BORDER_LIGHT};'>{cat_label}</td>"
                        f"<td style='padding:6px 10px; border-bottom:1px solid {T.BORDER_LIGHT};'>{st}</td>"
                        f"<td style='padding:6px 10px; border-bottom:1px solid {T.BORDER_LIGHT};'>{info['conformant']}/{info['total']}</td></tr>")
        html.append("</table>")

        try:
            layers = list_layers(Path(report.file_path))
            html.append(f"<h4 style='color:{T.TEXT_PRIMARY}; font-weight:600; margin-top:10px; font-size:12px;'>{t('lbl_layers')}</h4><div style='margin-bottom:6px;'>")
            for c in layers:
                exp = any(c.upper() == e.upper() for e in EXPECTED_LAYERS)
                clr2 = T.SUCCESS if exp else T.TEXT_SECONDARY
                bdr2 = T.SUCCESS if exp else T.BORDER
                bbg  = T.SUCCESS_BG if exp else T.SURFACE_ALT
                html.append(f"<div style='background:{bbg}; border:1px solid {bdr2}; color:{clr2}; border-radius:3px; padding:2px 8px; margin:2px 0; font-size:11px; font-weight:600;'>{c}</div>")
            html.append("</div>")
        except Exception:
            pass

        divs = [c for c in report.checks if c.status == Status.NON_CONFORMANT]
        if divs:
            html.append(f"<div style='background:{T.ERROR_BG}; border-left:4px solid {T.ERROR}; padding:10px 14px; border-radius:4px; margin-top:10px;'>"
                        f"<b style='color:{T.ERROR};'>{t('lbl_non_conf')} ({len(divs)})</b>"
                        f"<ul style='margin:4px 0; padding-left:16px; font-size:11px;'>")
            for ch in divs[:15]:
                lyr = f" [{ch.layer}]" if ch.layer else ""
                html.append(f"<li><b>{self._translate_check_name(ch.name)}</b>{lyr}: {self._translate_detail(ch.details)}</li>")
            if len(divs) > 15:
                html.append(f"<li><i>{t('lbl_and_more', n=len(divs)-15)}</i></li>")
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
            QMessageBox.warning(self, self._t("warn_export"), self._t("warn_export_msg"))
            return
        date_str = datetime.now().strftime("%Y%m%d_%H%M")
        filepath, _ = QFileDialog.getSaveFileName(self, self._t("dlg_save_pdf"), f"report_{date_str}.pdf", self._t("dlg_pdf_filter"))
        if not filepath:
            return
        try:
            result_path = export_report_pdf(self.report, filepath, locale=self._locale)
            # Try to open the generated PDF with the system default viewer.
            # Falls back gracefully if no viewer is available.
            import sys as _sys
            import shutil as _shutil
            import subprocess as _sp

            _opened = False
            if _sys.platform == "win32":
                os.startfile(str(result_path))
                _opened = True
            elif _sys.platform == "darwin":
                _opened = True
                _sp.Popen(["open", str(result_path)])
            else:
                # Linux — try common openers in order of preference
                for _cmd in ("xdg-open", "evince", "okular", "firefox", "eog"):
                    if _shutil.which(_cmd):
                        _sp.Popen([_cmd, str(result_path)])
                        _opened = True
                        break

            if not _opened:
                # No viewer found — inform the user where the file was saved
                QMessageBox.information(
                    self,
                    self._t("pdf_saved_title"),
                    self._t("pdf_saved_no_viewer", path=str(result_path)),
                )
        except Exception as e:
            QMessageBox.critical(self, self._t("err_pdf"), self._t("err_pdf_msg", e=e))
