# SICAR AD — Validate Environmental Base Structure

[![Version](https://img.shields.io/badge/version-0.0.1-blue)](https://github.com/dataprev/qgis-plugin-validador/releases)
[![License](https://img.shields.io/badge/license-GPLv3-green)](LICENSE.txt)
[![QGIS](https://img.shields.io/badge/QGIS-3.22%2B-brightgreen)](https://qgis.org)
[![Status](https://img.shields.io/badge/status-experimental-orange)]()

> 🇧🇷 [Leia em Português](README_pt.md)

A QGIS plugin for logical consistency validation of environmental geospatial databases, aligned with **ISO 19157:2013** — *Geographic Information — Data Quality*.

Developed by **[Dataprev](https://www.dataprev.gov.br)** for the **SICAR AD** (Sistema de Cadastro Ambiental Rural — Análise Dinamizada) program, managed by the **Serviço Florestal Brasileiro (SFB)**.

---

## Features

Validates four logical consistency categories defined in ISO 19157:2013:

- **Format consistency** — verifies the file format (GeoPackage or ESRI File Geodatabase) and readability
- **Conceptual consistency** — checks layer names, attribute presence/absence, record count, and CRS
- **Domain consistency** — validates that `CLASSE` attribute values fall within defined domains per layer
- **Topological consistency** — detects null geometries, empty geometries, zero-area polygons, topology errors, and 3D coordinates

Results are exported as a structured CSV report with pass/fail status per rule.

---

## Requirements

- **QGIS** 3.22 or higher (up to 4.x)
- No additional Python dependencies required

---

## Installation

1. Download the latest release `.zip` file from the [Releases](https://github.com/dataprev/qgis-plugin-validador/releases) page.
2. In QGIS, open **Plugins → Manage and Install Plugins → Install from ZIP**.
3. Select the downloaded `.zip` file and click **Install Plugin**.
4. The plugin will appear under the **Plugins** menu as *SICAR AD — Validate Environmental Base Structure*.

> **Note:** This plugin is currently marked as **experimental**. Make sure to enable *Show also experimental plugins* in the plugin manager settings.

---

## Usage

1. Open QGIS and activate the plugin via **Plugins → SICAR AD → Validate Environmental Base Structure**.
2. In the plugin dialog, select the environmental database to validate (`.gpkg` file or `.gdb` folder).
3. Click **Validate**.
4. Review the results in the validation report panel.
5. Optionally export the results to a CSV file.

---

## Accepted Formats

| Format | Extension | Type |
|--------|-----------|------|
| GeoPackage | `.gpkg` | File |
| ESRI File Geodatabase | `.gdb` | Directory |

---

## Validation Rules

For the full list of validation rules, expected layers, attribute domains, and topological checks, see [VALIDATION_RULES.md](VALIDATION_RULES.md).

---

## Normative Reference

- **ISO 19157:2013** — Geographic information — Data quality
  - Logical consistency
    - Format consistency
    - Conceptual consistency
    - Domain consistency
    - Topological consistency

---

## Contributing

Bug reports and feature requests are welcome via [GitHub Issues](https://github.com/dataprev/qgis-plugin-validador/issues).

For code contributions, please open a pull request with a clear description of the proposed change.

---

## License

This project is licensed under the **GNU General Public License v3.0**. See [LICENSE.txt](LICENSE.txt) for details.

---

## Credits

Developed by **[Dataprev](https://www.dataprev.gov.br)**  
For the **Serviço Florestal Brasileiro (SFB)** — SICAR AD program  
Contact: sicar@dataprev.gov.br
