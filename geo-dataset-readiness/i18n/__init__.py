# -*- coding: utf-8 -*-
"""
i18n — Internationalisation package for geo-dataset-readiness.

Usage
-----
    from .i18n import I18n

    i18n = I18n("pt_BR")          # or I18n.from_qgis()
    t    = i18n.t                  # shortcut

    # UI string
    label = t("ui.btn_validate")

    # Engine check name
    name  = i18n.translate_check_name("Dataset format")

    # Engine detail (handles dynamic values via regex patterns)
    detail = i18n.translate_detail("131079 record(s)")

Adding a new language
---------------------
1. Copy ``i18n/en_US.json`` to ``i18n/<locale>.json``.
2. Translate the values (keep all keys, only translate values).
3. No Python code changes required — the loader discovers the file automatically.
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional

_I18N_DIR = os.path.dirname(__file__)
_DEFAULT_LOCALE = "en_US"
_FALLBACK_LOCALE = "en_US"

# Cache: locale → loaded catalogue dict
_CACHE: dict[str, dict] = {}


def _load_catalogue(locale: str) -> dict:
    """Load and cache a locale JSON file. Falls back to en_US on error."""
    if locale in _CACHE:
        return _CACHE[locale]

    path = os.path.join(_I18N_DIR, f"{locale}.json")
    if not os.path.isfile(path):
        if locale != _FALLBACK_LOCALE:
            return _load_catalogue(_FALLBACK_LOCALE)
        return {}

    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        data = {}

    _CACHE[locale] = data
    return data


def available_locales() -> list[str]:
    """Returns a list of all available locale codes (based on JSON files present)."""
    locales = []
    for fname in os.listdir(_I18N_DIR):
        if fname.endswith(".json") and not fname.startswith("_"):
            locales.append(fname[:-5])
    return sorted(locales)


def detect_qgis_locale() -> str:
    """
    Reads the QGIS UI locale from QSettings.
    Returns the closest available locale, or _DEFAULT_LOCALE if QGIS is unavailable.
    """
    try:
        from qgis.PyQt.QtCore import QSettings
        settings = QSettings()
        qgis_locale: str = (
            settings.value("locale/userLocale", "", type=str)
            or settings.value("locale/globalLocale", "", type=str)
            or ""
        )
        if qgis_locale:
            # Exact match first (e.g. "pt_BR")
            if qgis_locale in available_locales():
                return qgis_locale
            # Language-only fallback (e.g. "pt" → "pt_BR")
            lang = qgis_locale.split("_")[0].lower()
            for loc in available_locales():
                if loc.lower().startswith(lang):
                    return loc
    except Exception:
        pass
    return _DEFAULT_LOCALE


class I18n:
    """
    Internationalisation helper.

    Loads translations from ``i18n/<locale>.json`` and provides:
    - ``t(key)``                  — UI string lookup (dot-notation)
    - ``translate_check_name()``  — engine check name translation
    - ``translate_detail()``      — engine detail string translation (incl. regex)
    - ``translate_status()``      — Status enum value translation
    - ``localized_summary()``     — summary sentence construction
    - ``flag``                    — language button label (e.g. "🌐 PT")
    - ``locale``                  — current locale code
    """

    def __init__(self, locale: str = _DEFAULT_LOCALE) -> None:
        self._locale = locale
        self._data   = _load_catalogue(locale)
        self._fallback = _load_catalogue(_FALLBACK_LOCALE) if locale != _FALLBACK_LOCALE else {}

        # Pre-compile regex patterns from JSON (avoids re-compiling on every call)
        self._patterns: list[tuple[re.Pattern, str]] = []
        raw_patterns = (
            self._data.get("engine", {}).get("detail_patterns", [])
        )
        for pair in raw_patterns:
            if isinstance(pair, (list, tuple)) and len(pair) == 2:
                try:
                    self._patterns.append((re.compile(pair[0]), pair[1]))
                except re.error:
                    pass

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_qgis(cls) -> "I18n":
        """Create an I18n instance using the QGIS UI language."""
        return cls(detect_qgis_locale())

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def locale(self) -> str:
        return self._locale

    @property
    def flag(self) -> str:
        return self._data.get("_meta", {}).get("flag", "🌐")

    @property
    def language_name(self) -> str:
        return self._data.get("_meta", {}).get("language", self._locale)

    # ------------------------------------------------------------------
    # Core lookup
    # ------------------------------------------------------------------

    def t(self, key: str, **kwargs) -> str:
        """
        Look up a UI translation key using dot-notation.

        Examples::

            i18n.t("ui.btn_validate")
            i18n.t("ui.err_validation_msg", e="some error")
        """
        parts  = key.split(".")
        value  = self._data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = None
                break

        if value is None:
            # Try fallback locale
            value = self._fallback
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    value = None
                    break

        if not isinstance(value, str):
            # Return the last key part as a last-resort placeholder
            return key.split(".")[-1]

        if kwargs:
            try:
                return value.format(**kwargs)
            except (KeyError, ValueError):
                return value
        return value

    # ------------------------------------------------------------------
    # Engine output translation
    # ------------------------------------------------------------------

    def translate_status(self, status_value: str) -> str:
        """Translate a Status enum value (CONFORMANT, NON-CONFORMANT, WARNING)."""
        status_map = self._data.get("engine", {}).get("status", {})
        return status_map.get(status_value, status_value)

    def translate_check_name(self, name: str) -> str:
        """
        Translate a check name produced by the validation engine.
        Supports prefix match for dynamic names like 'Error in feature FID 42'.
        """
        names = self._data.get("engine", {}).get("check_names", {})
        if not names:
            return name
        if name in names:
            return names[name]
        # Prefix match for dynamic names
        for en_key, pt_val in names.items():
            if name.startswith(en_key):
                return pt_val + name[len(en_key):]
        return name

    def translate_detail(self, detail: str) -> str:
        """
        Translate an engine detail string.

        Strategy (in order of cost):
        1. Exact match in ``engine.detail_exact``
        2. Regex pattern match in ``engine.detail_patterns``
        3. Return original string unchanged
        """
        if self._locale == _FALLBACK_LOCALE:
            return detail

        exact = self._data.get("engine", {}).get("detail_exact", {})
        if detail in exact:
            return exact[detail]

        for pattern, template in self._patterns:
            m = pattern.match(detail)
            if m:
                return m.expand(template)

        return detail

    def localized_summary(self, total: int, ok: int, non_conf: int, warnings: int) -> str:
        tmpl = self._data.get("engine", {}).get("summary", {})
        if not tmpl:
            tmpl = self._fallback.get("engine", {}).get("summary", {})

        parts = [tmpl.get("rules_executed", "{total} rules ({ok} ok").format(
            total=total, ok=ok
        )]
        if non_conf:
            parts.append(tmpl.get("non_conformant", ", {n} non-conformant").format(n=non_conf))
        if warnings:
            parts.append(tmpl.get("warnings", ", {n} warning(s)").format(n=warnings))
        parts.append(tmpl.get("close", ")"))
        return "".join(parts)

    def get_progress_messages(self) -> dict[str, str]:
        """
        Returns the progress message templates for the current locale.
        Falls back to en_US if a key is missing.
        """
        en_prog = self._fallback.get("engine", {}).get("progress", {}) if self._fallback else {}
        loc_prog = self._data.get("engine", {}).get("progress", {})
        # Merge: locale overrides fallback
        merged = {**en_prog, **loc_prog}
        return merged
