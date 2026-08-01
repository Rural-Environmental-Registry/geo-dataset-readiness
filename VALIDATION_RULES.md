# Validation Rules — SICAR AD

> 🇧🇷 Este documento está em inglês por ser o idioma oficial do repositório.  
> As regras refletem o modelo conceitual da base ambiental do SICAR AD.

This document describes all validation rules executed by the plugin, organized by logical consistency category as defined in **ISO 19157:2013**.

---

## 1. Format Consistency

Verifies whether the geographic database is in a valid format and can be read.

| # | Rule | Description | Possible Status |
|---|------|-------------|-----------------|
| 1.1 | Database format | The database must be in GeoPackage (.gpkg) or ESRI File Geodatabase (.gdb) format | COMPLIANT / NON-COMPLIANT |
| 1.2 | Database readability | The file must be readable and contain at least one geographic layer | COMPLIANT / NON-COMPLIANT |

---

## 2. Conceptual Consistency

Verifies whether the database structure (layer names, attributes, and coordinate reference system) matches the expected conceptual model.

| # | Rule | Description | Possible Status |
|---|------|-------------|-----------------|
| 2.1 | Layer names | The database must contain the 10 expected layers (case-insensitive comparison) | COMPLIANT / NON-COMPLIANT |
| 2.2 | Records per layer | Each present layer must have at least one record | COMPLIANT / NON-COMPLIANT |
| 2.3 | CLASSE attribute (presence) | Layers that must have CLASSE: HIDROGRAFIA, APP, SERVIDAO, RELEVO, USO_RESTRITO, APP_ESPECIAL | COMPLIANT / NON-COMPLIANT |
| 2.4 | CLASSE attribute (absence) | Layers that must not have CLASSE: AREA_ANTROPIZADA, AREA_CONSOLIDADA, VEGETACAO_ATUAL, VEGETACAO_2008 | COMPLIANT / NON-COMPLIANT |
| 2.5 | Coordinate Reference System (CRS) | All layers must be in SIRGAS 2000 Geographic (EPSG:4674) | COMPLIANT / NON-COMPLIANT |

### Expected Layers

| Layer | Must Have CLASSE | CLASSE Domain |
|-------|:----------------:|---------------|
| AREA_ANTROPIZADA | No | — |
| AREA_CONSOLIDADA | No | — |
| HIDROGRAFIA | Yes | 1 to 8 |
| APP | Yes | 1 to 8 |
| VEGETACAO_ATUAL | No | — |
| VEGETACAO_2008 | No | — |
| SERVIDAO | Yes | 1 to 4 |
| RELEVO | Yes | 1 to 8 |
| USO_RESTRITO | Yes | 1 to 2 |
| APP_ESPECIAL | Yes | 1 to 10 |

---

## 3. Domain Consistency

Verifies whether the values of the `CLASSE` attribute fall within the expected domain.

| # | Rule | Description | Possible Status |
|---|------|-------------|-----------------|
| 3.1 | CLASSE numeric type | The CLASSE attribute must be of numeric type (integer or float) | COMPLIANT / NON-COMPLIANT |
| 3.2 | CLASSE null values | Null values are not allowed in the CLASSE attribute | COMPLIANT / NON-COMPLIANT |
| 3.3 | CLASSE distinct values | Informational record of distinct values found | COMPLIANT / NON-COMPLIANT |
| 3.4 | CLASSE domain | Values must fall within the defined range for each layer | COMPLIANT / NON-COMPLIANT |

### Valid Ranges per Layer (CLASSE attribute)

| Layer | Valid Range |
|-------|-------------|
| HIDROGRAFIA | 1 to 8 |
| APP | 1 to 8 |
| SERVIDAO | 1 to 4 |
| USO_RESTRITO | 1 to 2 |
| RELEVO | 1 to 8 |
| APP_ESPECIAL | 1 to 10 |

### Subclassification per Layer

#### APP (Classes 1 to 8)

| Class | Description |
|-------|-------------|
| 1 | APP_RIO_ATE_10 |
| 2 | APP_RIO_10_A_50 |
| 3 | APP_RIO_50_A_200 |
| 4 | APP_RIO_200_A_600 |
| 5 | APP_RIO_ACIMA_600 |
| 6 | APP_LAGO_NATURAL |
| 7 | APP_RESERVATORIO_ARTIFICIAL |
| 8 | APP_NASCENTE |

#### HIDROGRAFIA (Classes 1 to 8)

| Class | Description |
|-------|-------------|
| 1 | RIO_ATE_10 |
| 2 | RIO_10_A_50 |
| 3 | RIO_50_A_200 |
| 4 | RIO_200_A_600 |
| 5 | RIO_ACIMA_600 |
| 6 | LAGO_NATURAL |
| 7 | RESERVATORIO_ARTIFICIAL |
| 8 | NASCENTE |

#### USO_RESTRITO (Classes 1 to 2)

| Class | Description |
|-------|-------------|
| 1 | DECLIVIDADE_25_A_45 |
| 2 | PANTANEIRA |

#### SERVIDAO (Classes 1 to 4)

| Class | Description |
|-------|-------------|
| 1 | INFRAESTRUTURA_PUBLICA |
| 2 | UTILIDADE_PUBLICA |
| 3 | RESERVATORIO_ABASTECIMENTO_GERACAO_ENERGIA |
| 4 | ENTORNO_RESERVATORIO_ABASTECIMENTO_GERACAO_ENERGIA |

#### RELEVO (Classes 1 to 8)

| Class | Description |
|-------|-------------|
| 1 | ALTITUDE_SUPERIOR_1800 |
| 2 | BORDA_CHAPADA |
| 3 | DECLIVIDADE_MAIOR_45 |
| 4 | TOPO_MORRO |
| 5 | APP_ALTITUDE_SUPERIOR_1800 |
| 6 | APP_BORDA_CHAPADA |
| 7 | APP_DECLIVIDADE_MAIOR_45 |
| 8 | APP_TOPO_MORRO |

#### APP_ESPECIAL (Classes 1 to 10)

| Class | Description |
|-------|-------------|
| 1 | RESERVATORIO_ENERGIA_24082001 |
| 2 | VEGETACAO_RESTINGA |
| 3 | VEGETACAO_VEREDA |
| 4 | VEGETACAO_BANHADO |
| 5 | VEGETACAO_MANGUEZAL |
| 6 | APP_RESERVATORIO_ENERGIA_24082001 |
| 7 | APP_RESTINGA |
| 8 | APP_VEREDA |
| 9 | APP_BANHADO |
| 10 | APP_MANGUEZAL |

---

## 4. Topological Consistency

Verifies the geometric integrity of records in each layer.

| # | Rule | Description | Possible Status |
|---|------|-------------|-----------------|
| 4.1 | Null geometries | No record may have a null geometry | COMPLIANT / NON-COMPLIANT |
| 4.2 | Empty geometries | No record may have an empty geometry | COMPLIANT / NON-COMPLIANT |
| 4.3 | Zero-area polygons | No polygon may have an area equal to zero | COMPLIANT / NON-COMPLIANT |
| 4.4 | Topological errors | All geometries must be topologically valid (no self-intersections, inverted rings, etc.) | COMPLIANT / NON-COMPLIANT |
| 4.5 | 2D dimension | All geometries must be two-dimensional (no Z coordinate) | COMPLIANT / NON-COMPLIANT |

---

## Notes

- Layer name comparison is **case-insensitive**.
- Empty layers (0 records) are reported as non-compliant in conceptual consistency; topological consistency ignores layers with no data.
- The expected CRS is **EPSG:4674** (SIRGAS 2000 Geographic) for all layers.

---

## Normative Reference

- **ISO 19157:2013** — Geographic information — Data quality
  - Quality element: **Logical Consistency**
    - Format consistency
    - Conceptual consistency
    - Domain consistency
    - Topological consistency
