# -*- coding: utf-8 -*-
"""
renomeia_camada_gpkg.py
=======================
Renames an internal layer of a GeoPackage (.gpkg) file.

The GeoPackage format stores layer names in multiple places that must be kept
in sync:
    1. The actual SQLite table name.
    2. The gpkg_contents and gpkg_geometry_columns system tables.
    3. The spatial index R-Tree virtual table.

R-Tree virtual tables CANNOT be renamed with ALTER TABLE — SQLite manages
shadow tables (_rowid, _node, _parent, _chunks) internally and raises
OperationalError if you attempt to rename them directly.  The correct
approach is to DROP the old virtual table and CREATE a new one with the
new name, then populate it from the renamed data table.

Usage
-----
    python renomeia_camada_gpkg.py <arquivo.gpkg> <nome_atual> <novo_nome>

    # Example
    python renomeia_camada_gpkg.py C:/data/base.gpkg VEGETACAO_ATUAL VEGETACAO

Dependencies
------------
    - Python standard library only (sqlite3).
    - No QGIS or GDAL required at runtime.

Notes
-----
    - A backup (<arquivo>.gpkg.bak) is created before any modification.
      Delete it manually when satisfied with the result.
    - Layer name lookup is case-insensitive.
    - The rename is refused if the new name already exists as a table.
"""

import os
import sys
import shutil
import sqlite3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log(msg: str, level: str = "INFO") -> None:
    prefix = {"INFO": "✔", "WARN": "⚠", "ERRO": "✘", "PROG": "→"}.get(level, " ")
    print(f"  {prefix}  [{level}] {msg}")


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
        (name,)
    )
    return cur.fetchone()[0] > 0


def _list_layers(conn: sqlite3.Connection) -> list[str]:
    try:
        cur = conn.execute("SELECT table_name FROM gpkg_contents ORDER BY table_name")
        return [row[0] for row in cur.fetchall()]
    except sqlite3.OperationalError:
        return []


def _find_layer(conn: sqlite3.Connection, name: str) -> str | None:
    """Case-insensitive lookup in gpkg_contents. Returns exact stored name or None."""
    cur = conn.execute(
        "SELECT table_name FROM gpkg_contents WHERE lower(table_name) = lower(?)",
        (name,)
    )
    row = cur.fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# Main rename function
# ---------------------------------------------------------------------------

def rename_layer(gpkg_path: str, old_name: str, new_name: str) -> None:
    """
    Renames a layer inside a GeoPackage.

    Parameters
    ----------
    gpkg_path : str  — path to the .gpkg file (must exist and be writable).
    old_name  : str  — current layer name (case-insensitive match).
    new_name  : str  — new layer name (must not already exist as a table).

    Raises
    ------
    FileNotFoundError  — gpkg_path does not exist.
    ValueError         — invalid parameters or name conflict.
    RuntimeError       — database operation failed.
    """
    gpkg_path = os.path.abspath(gpkg_path)

    # ── Validate inputs ───────────────────────────────────────────────────
    if not os.path.isfile(gpkg_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {gpkg_path}")
    if not gpkg_path.lower().endswith(".gpkg"):
        raise ValueError(f"O arquivo informado não é um .gpkg: {gpkg_path}")
    if not old_name or not new_name:
        raise ValueError("Os nomes da camada não podem ser vazios.")
    if old_name == new_name:
        raise ValueError(
            f"O nome novo é idêntico ao atual: '{old_name}'. Nenhuma alteração necessária."
        )

    _log(f"Arquivo  : {gpkg_path}")
    _log(f"Camada   : '{old_name}'  →  '{new_name}'")
    print()

    # ── Backup ───────────────────────────────────────────────────────────
    bak_path = gpkg_path + ".bak"
    _log(f"Criando backup em: {bak_path}", "PROG")
    shutil.copy2(gpkg_path, bak_path)
    _log("Backup criado.")

    # ── Connect ──────────────────────────────────────────────────────────
    conn = sqlite3.connect(gpkg_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=OFF;")

    try:
        # ── Locate layer ─────────────────────────────────────────────────
        exact_old = _find_layer(conn, old_name)
        if exact_old is None:
            layers = _list_layers(conn)
            msg = f"Camada '{old_name}' não encontrada no GeoPackage."
            if layers:
                msg += "\nCamadas disponíveis:\n  " + "\n  ".join(layers)
            raise ValueError(msg)

        if _table_exists(conn, new_name):
            raise ValueError(
                f"Já existe uma tabela com o nome '{new_name}' no arquivo. "
                "Escolha outro nome para evitar perda de dados."
            )

        _log(f"Camada encontrada (nome exato): '{exact_old}'", "PROG")
        print()

        with conn:

            # 1. Rename the data table
            _log("1/5  Renomeando tabela SQLite...", "PROG")
            conn.execute(f'ALTER TABLE "{exact_old}" RENAME TO "{new_name}";')

            # 2. gpkg_contents
            _log("2/5  Atualizando gpkg_contents...", "PROG")
            conn.execute(
                "UPDATE gpkg_contents SET table_name = ? WHERE table_name = ?",
                (new_name, exact_old)
            )

            # 3. gpkg_geometry_columns
            _log("3/5  Atualizando gpkg_geometry_columns...", "PROG")
            try:
                conn.execute(
                    "UPDATE gpkg_geometry_columns SET table_name = ? WHERE table_name = ?",
                    (new_name, exact_old)
                )
            except sqlite3.OperationalError:
                _log("gpkg_geometry_columns não encontrada (camada sem geometria).", "WARN")

            # 4. gpkg_tile_matrix_set (raster layers — best effort)
            _log("4/5  Verificando gpkg_tile_matrix_set...", "PROG")
            try:
                conn.execute(
                    "UPDATE gpkg_tile_matrix_set SET table_name = ? WHERE table_name = ?",
                    (new_name, exact_old)
                )
            except sqlite3.OperationalError:
                pass

            # 5. Spatial index (R-Tree virtual table)
            #
            #    WHY NOT ALTER TABLE:
            #    R-Tree virtual tables have shadow tables (_rowid, _node,
            #    _parent, _chunks) managed internally by SQLite.  Attempting
            #    ALTER TABLE on them raises OperationalError: "no such table".
            #
            #    CORRECT APPROACH:
            #    a) DROP the old virtual table (SQLite cascades to all shadows)
            #    b) CREATE a new virtual table with the new name
            #    c) Populate it from the renamed data table
            _log("5/5  Recriando índice espacial com o novo nome...", "PROG")

            # Get geometry column name from gpkg_geometry_columns
            cur = conn.execute(
                "SELECT column_name FROM gpkg_geometry_columns WHERE table_name = ?",
                (new_name,)
            )
            geom_col_row = cur.fetchone()
            geom_col = geom_col_row[0] if geom_col_row else "geom"

            old_rtree = f"rtree_{exact_old}_{geom_col}"
            new_rtree = f"rtree_{new_name}_{geom_col}"

            # Check whether an R-Tree exists for this layer
            cur2 = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master "
                "WHERE type='table' AND name = ?",
                (old_rtree,)
            )
            rtree_exists = cur2.fetchone()[0] > 0

            if rtree_exists:
                # a) Drop old virtual table + all shadow tables
                conn.execute(f'DROP TABLE IF EXISTS "{old_rtree}";')
                _log(f"    Índice antigo removido: '{old_rtree}'", "INFO")

                # b) Recreate with new name
                conn.execute(
                    f'CREATE VIRTUAL TABLE "{new_rtree}" '
                    f'USING rtree(id, minx, maxx, miny, maxy);'
                )

                # c) Populate from renamed data table
                conn.execute(
                    f'INSERT INTO "{new_rtree}" '
                    f'SELECT fid, '
                    f'  ST_MinX("{geom_col}"), ST_MaxX("{geom_col}"), '
                    f'  ST_MinY("{geom_col}"), ST_MaxY("{geom_col}") '
                    f'FROM "{new_name}" '
                    f'WHERE "{geom_col}" IS NOT NULL;'
                )
                _log(f"    Índice recriado e populado: '{new_rtree}'", "INFO")

                # Update gpkg_extensions reference (best effort)
                try:
                    conn.execute(
                        "UPDATE gpkg_extensions SET table_name = ? "
                        "WHERE table_name = ?",
                        (new_name, exact_old)
                    )
                except sqlite3.OperationalError:
                    pass
            else:
                _log(
                    "    Nenhum índice espacial encontrado "
                    "(normal para camadas sem geometria ou sem índice).",
                    "WARN"
                )

        # ── Verify ────────────────────────────────────────────────────────
        confirmed = _find_layer(conn, new_name)
        if confirmed is None:
            raise RuntimeError(
                "A camada não aparece com o novo nome em gpkg_contents. "
                "Restaure o backup e verifique o arquivo."
            )

        conn.execute("PRAGMA integrity_check;")

    except Exception:
        conn.close()
        raise
    finally:
        if conn:
            conn.close()

    print()
    _log(f"Camada renomeada com sucesso: '{exact_old}' → '{new_name}'")
    _log(f"Backup disponível em: {bak_path}")
    _log("Delete o backup manualmente quando confirmar que está tudo correto.", "WARN")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__)
        print(
            "Uso: python renomeia_camada_gpkg.py "
            "<arquivo.gpkg> <nome_atual> <novo_nome>"
        )
        return 1

    gpkg = sys.argv[1].strip().strip('"')
    old  = sys.argv[2].strip()
    new  = sys.argv[3].strip()

    print()
    print("=" * 60)
    print("  Renomear Camada GeoPackage")
    print("=" * 60)
    print()

    try:
        rename_layer(gpkg, old, new)
        return 0
    except (FileNotFoundError, ValueError) as exc:
        print()
        _log(str(exc), "ERRO")
        return 2
    except RuntimeError as exc:
        print()
        _log(str(exc), "ERRO")
        return 3
    except Exception as exc:
        print()
        _log(f"Erro inesperado: {exc}", "ERRO")
        import traceback
        traceback.print_exc()
        return 4


if __name__ == "__main__":
    sys.exit(main())
