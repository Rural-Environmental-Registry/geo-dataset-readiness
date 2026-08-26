# -*- coding: utf-8 -*-
"""
criar_bases_teste.py
====================
Creates the 12 test GeoPackage/GDB bases required for SICAR AD plugin
homologation testing.

All bases are written to:
    tests/data/bases_teste/

Dependencies: geopandas, shapely, pyogrio (all included in QGIS Python env)

Run with the QGIS Python interpreter or any Python >= 3.9 that has
geopandas + pyogrio installed.
"""

import os
import sys
import zipfile
import shutil

try:
    import geopandas as gpd
    import pandas as pd
    from shapely.geometry import (
        MultiPolygon, Polygon, mapping
    )
    from shapely import wkt as shapely_wkt
except ImportError as e:
    sys.exit(f"[ERRO] Biblioteca ausente: {e}\n"
             "Execute com o Python do QGIS ou instale geopandas + shapely.")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR    = os.path.join(SCRIPT_DIR, "bases_teste")  # tests/data/bases_teste/
os.makedirs(OUT_DIR, exist_ok=True)

def out(name):
    return os.path.join(OUT_DIR, name)

# ---------------------------------------------------------------------------
# Layer definitions: which layers carry CLASSE and their valid domains
# ---------------------------------------------------------------------------
LAYERS_WITH_CLASSE = {
    "HIDROGRAFIA":  (1, 8),
    "APP":          (1, 8),
    "SERVIDAO":     (1, 4),
    "RELEVO":       (1, 8),
    "USO_RESTRITO": (1, 2),
    "APP_ESPECIAL": (1, 10),
}
LAYERS_WITHOUT_CLASSE = [
    "AREA_ANTROPIZADA",
    "AREA_CONSOLIDADA",
    "VEGETACAO_ATUAL",
    "VEGETACAO_2008",
]
ALL_LAYERS = LAYERS_WITHOUT_CLASSE + list(LAYERS_WITH_CLASSE.keys())

# ---------------------------------------------------------------------------
# Geometry factory — simple valid 2D polygons spread across RN state (Brazil)
# Each call shifts the polygon slightly so they don't overlap.
# ---------------------------------------------------------------------------
_offset = 0.0

def make_poly(n=1, z=False):
    """Return a list of n valid MultiPolygon geometries."""
    global _offset
    geoms = []
    for i in range(n):
        lon = -37.0 - _offset - i * 0.01
        lat = -6.0  - _offset - i * 0.01
        ring = [
            (lon,       lat),
            (lon+0.005, lat),
            (lon+0.005, lat+0.005),
            (lon,       lat+0.005),
            (lon,       lat),
        ]
        if z:
            ring = [(x, y, 0.0) for x, y in ring]
        poly = Polygon(ring)
        geoms.append(MultiPolygon([poly]))
    _offset += 0.001
    return geoms


def make_gdf(geoms, crs="EPSG:4674", classe_vals=None, classe_type="int"):
    """Build a GeoDataFrame."""
    data = {"geometry": geoms}
    if classe_vals is not None:
        data["CLASSE"] = classe_vals
    gdf = gpd.GeoDataFrame(data, geometry="geometry", crs=crs)
    if classe_vals is not None and classe_type == "str":
        gdf["CLASSE"] = gdf["CLASSE"].astype(str)
    return gdf


def save_layer(gdf, path, layer, overwrite=False):
    """Write a layer to a GeoPackage. overwrite=True replaces existing layer."""
    mode = "w" if overwrite or not os.path.exists(path) else "a"
    gdf.to_file(path, layer=layer, driver="GPKG", engine="pyogrio", mode=mode)


def full_valid_base(path, name_map=None, crs_override=None, skip_layers=None,
                    extra_layer=False):
    """
    Write a complete, valid base to path.
    name_map  : {logical_name: written_name}  (for TC-12 name case test)
    crs_override : {layer_name: crs_string}
    skip_layers  : list of layer names to omit
    extra_layer  : add an unexpected layer
    """
    if os.path.exists(path):
        os.remove(path)
    skip_layers = skip_layers or []
    name_map    = name_map or {}
    crs_override = crs_override or {}

    for layer in ALL_LAYERS:
        if layer in skip_layers:
            continue
        written = name_map.get(layer, layer)
        crs     = crs_override.get(layer, "EPSG:4674")
        if layer in LAYERS_WITH_CLASSE:
            lo, hi  = LAYERS_WITH_CLASSE[layer]
            n       = hi - lo + 1
            geoms   = make_poly(n)
            classes = list(range(lo, hi + 1))
            gdf     = make_gdf(geoms, crs=crs, classe_vals=classes)
        else:
            gdf = make_gdf(make_poly(3), crs=crs)
        save_layer(gdf, path, written)

    if extra_layer:
        gdf_extra = make_gdf(make_poly(1))
        save_layer(gdf_extra, path, "EXTRA_LAYER")


def log(msg, level="INFO"):
    icons = {"INFO":"[OK]","WARN":"[AV]","ERRO":"[ERR]","PROG":"[>>]"}
    print(f"  {icons.get(level,'   ')}  [{level}] {msg}")

# ===========================================================================
# B01 — Complete, valid base (.gpkg)
# ===========================================================================
def make_b01():
    path = out("B01_base_valida.gpkg")
    full_valid_base(path, extra_layer=True)
    log(f"B01 criada: {path}")
    return path

# ===========================================================================
# B02 — Complete, valid base (.gdb)  — uses GeoPackage layers converted
# ===========================================================================
def make_b02():
    # Write each layer to a tmp gpkg first, then copy to gdb via pyogrio
    tmp = out("_b02_tmp.gpkg")
    full_valid_base(tmp)
    gdb_path = out("B02_base_valida.gdb")
    if os.path.exists(gdb_path):
        shutil.rmtree(gdb_path)
    import pyogrio
    layers = pyogrio.list_layers(tmp)
    for lname, _ in layers:
        gdf = gpd.read_file(tmp, layer=lname, engine="pyogrio")
        gdf.to_file(gdb_path, layer=lname, driver="OpenFileGDB", engine="pyogrio")
    os.remove(tmp)
    log(f"B02 criada: {gdb_path}")
    return gdb_path

# ===========================================================================
# B03 — ZIP containing B01 .gpkg
# ===========================================================================
def make_b03(b01_path):
    zip_path = out("B03_base_valida_zipada.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(b01_path, arcname=os.path.basename(b01_path))
    log(f"B03 criada: {zip_path}")
    return zip_path

# ===========================================================================
# B04 — Corrupted .gpkg (text file with .gpkg extension)
# ===========================================================================
def make_b04():
    path = out("B04_corrompido.gpkg")
    with open(path, "w", encoding="utf-8") as f:
        f.write("Este arquivo não é um GeoPackage válido.\n")
    log(f"B04 criada: {path}")
    return path

# ===========================================================================
# B05 — Empty .gpkg (no layers)
# ===========================================================================
def make_b05():
    path = out("B05_vazio.gpkg")
    if os.path.exists(path): os.remove(path)
    # Create an empty GeoPackage by writing an empty GDF and then deleting it
    # The simplest way: use sqlite3 to create a valid GeoPackage schema
    import sqlite3
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gpkg_spatial_ref_sys (
            srs_name TEXT NOT NULL, srs_id INTEGER NOT NULL PRIMARY KEY,
            organization TEXT NOT NULL, organization_coordsys_id INTEGER NOT NULL,
            definition TEXT NOT NULL, description TEXT)""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gpkg_contents (
            table_name TEXT NOT NULL PRIMARY KEY, data_type TEXT NOT NULL,
            identifier TEXT, description TEXT, last_change DATETIME,
            min_x REAL, min_y REAL, max_x REAL, max_y REAL, srs_id INTEGER)""")
    conn.execute("PRAGMA application_id = 1196444487;")
    conn.commit(); conn.close()
    log(f"B05 criada: {path}")
    return path

# ===========================================================================
# B06 — Missing layers + empty layer + 1-record layer + lowercase name
# ===========================================================================
def make_b06():
    path = out("B06_camadas_ausentes.gpkg")
    full_valid_base(
        path,
        skip_layers=["VEGETACAO_ATUAL", "APP"],        # TC-10 obrigatória, TC-11 opcional
        name_map={"VEGETACAO_2008": "vegetacao_2008"}, # TC-12 lowercase
    )
    # TC-13: HIDROGRAFIA with 0 records — write empty layer
    gdf_hi_empty = gpd.GeoDataFrame(
        {"geometry": gpd.GeoSeries([], dtype="geometry"), "CLASSE": pd.array([], dtype="Int64")},
        geometry="geometry", crs="EPSG:4674")
    save_layer(gdf_hi_empty, path, "HIDROGRAFIA", overwrite=True)

    # TC-14: AREA_ANTROPIZADA with exactly 1 record
    gdf_1 = make_gdf(make_poly(1), crs="EPSG:4674")
    save_layer(gdf_1, path, "AREA_ANTROPIZADA", overwrite=True)
    log(f"B06 criada: {path}")
    return path

# ===========================================================================
# B07 — CLASSE errors
# ===========================================================================
def make_b07():
    path = out("B07_erros_classe.gpkg")
    full_valid_base(path)
    # TC-17: HIDROGRAFIA sem CLASSE — rewrite without CLASSE field
    gdf_no_classe = make_gdf(make_poly(3), crs="EPSG:4674")
    save_layer(gdf_no_classe, path, "HIDROGRAFIA", overwrite=True)
    # TC-18: AREA_CONSOLIDADA COM CLASSE (forbidden) — rewrite with CLASSE
    gdf_with_classe = make_gdf(make_poly(3), crs="EPSG:4674", classe_vals=[1,2,3])
    save_layer(gdf_with_classe, path, "AREA_CONSOLIDADA", overwrite=True)
    log(f"B07 criada: {path}")
    return path

# ===========================================================================
# B08 — CRS errors per layer
# ===========================================================================
def make_b08():
    path = out("B08_erros_crs.gpkg")
    full_valid_base(path, crs_override={
        "HIDROGRAFIA":    "EPSG:4326",   # TC-21 AVISO
        "APP":            "EPSG:3857",   # TC-22 AVISO
        "VEGETACAO_ATUAL":"EPSG:31983",  # TC-23 DIVERGÊNCIA
    })
    # TC-24: VEGETACAO_2008 sem CRS — write without CRS
    gdf_no_crs = gpd.GeoDataFrame({"geometry": make_poly(2)}, geometry="geometry")
    gdf_no_crs.crs = None
    save_layer(gdf_no_crs, path, "VEGETACAO_2008", overwrite=True)
    log(f"B08 criada: {path}")
    return path

# ===========================================================================
# B09 — Domain errors in CLASSE
# ===========================================================================
def make_b09():
    path = out("B09_erros_dominio.gpkg")
    full_valid_base(path)

    # TC-26: HIDROGRAFIA com valor 9 fora do domínio [1,8]
    gdf26 = make_gdf(make_poly(3), crs="EPSG:4674", classe_vals=[1, 5, 9])
    save_layer(gdf26, path, "HIDROGRAFIA", overwrite=True)

    # TC-27: APP com alguns NULL
    gdf27 = make_gdf(make_poly(4), crs="EPSG:4674", classe_vals=[1, None, 3, None])
    save_layer(gdf27, path, "APP", overwrite=True)

    # TC-28: SERVIDAO com CLASSE texto não numérico
    gdf28 = make_gdf(make_poly(3), crs="EPSG:4674",
                     classe_vals=["A", "B", "C"], classe_type="str")
    save_layer(gdf28, path, "SERVIDAO", overwrite=True)

    # TC-29: RELEVO com CLASSE texto conversível ("1","2","3")
    gdf29 = make_gdf(make_poly(3), crs="EPSG:4674",
                     classe_vals=["1", "2", "3"], classe_type="str")
    save_layer(gdf29, path, "RELEVO", overwrite=True)

    log(f"B09 criada: {path}")
    return path

# ===========================================================================
# B10 — Topological errors
# ===========================================================================
def make_b10():
    from shapely.geometry import MultiPolygon, Polygon
    path = out("B10_erros_topologicos.gpkg")
    full_valid_base(path)

    # TC-31: VEGETACAO_ATUAL — some NULL geometries
    geoms31 = make_poly(5)
    geoms31[1] = None
    geoms31[3] = None
    gdf31 = gpd.GeoDataFrame({"geometry": geoms31}, geometry="geometry", crs="EPSG:4674")
    save_layer(gdf31, path, "VEGETACAO_ATUAL", overwrite=True)

    # TC-32: VEGETACAO_2008 — some EMPTY geometries
    geoms32 = make_poly(5)
    geoms32[2] = MultiPolygon()
    gdf32 = gpd.GeoDataFrame({"geometry": geoms32}, geometry="geometry", crs="EPSG:4674")
    save_layer(gdf32, path, "VEGETACAO_2008", overwrite=True)

    # TC-33: APP — MultiPolygon Z (3D) — build directly with Shapely
    from shapely.geometry import MultiPolygon as MP
    def poly_z(idx=0):
        from shapely.geometry import Polygon as Poly
        lon, lat = -36.5 + idx * 0.01, -6.5
        ring = [
            (lon, lat, 0), (lon+0.005, lat, 0),
            (lon+0.005, lat+0.005, 0), (lon, lat+0.005, 0),
            (lon, lat, 0),
        ]
        return MP([Poly(ring)])
    geoms33 = [poly_z(i) for i in range(4)]
    gdf33 = gpd.GeoDataFrame(
        {"geometry": geoms33, "CLASSE": [1, 2, 3, 4]}, geometry="geometry", crs="EPSG:4674")
    save_layer(gdf33, path, "APP", overwrite=True)

    # TC-34: HIDROGRAFIA — "Holes are nested" (HARD_ERROR — counted directly
    # by the validator without make_valid / area_ratio filtering)
    def nested_holes_poly(lon_offset=0.0):
        from shapely.geometry import Polygon
        lo = -36.0 + lon_offset; la = -6.0
        exterior = [(lo,la),(lo+0.10,la),(lo+0.10,la-0.10),(lo,la-0.10),(lo,la)]
        hole1    = [(lo+0.02,la-0.02),(lo+0.08,la-0.02),(lo+0.08,la-0.08),(lo+0.02,la-0.08),(lo+0.02,la-0.02)]
        hole2    = [(lo+0.03,la-0.03),(lo+0.07,la-0.03),(lo+0.07,la-0.07),(lo+0.03,la-0.07),(lo+0.03,la-0.03)]
        return MultiPolygon([Polygon(exterior, [hole1, hole2])])
    geoms34 = [nested_holes_poly(i * 0.15) for i in range(4)]
    gdf34 = gpd.GeoDataFrame(
        {"geometry": geoms34, "CLASSE": [1, 2, 3, 4]}, geometry="geometry", crs="EPSG:4674")
    save_layer(gdf34, path, "HIDROGRAFIA", overwrite=True)

    # TC-35: AREA_ANTROPIZADA — ring self-intersection via floating-point
    lon, lat = -35.0, -6.0
    eps = 1e-14
    ring_si = [
        (lon, lat), (lon+0.005, lat), (lon+0.005, lat+0.005),
        (lon, lat+0.005), (lon+eps, lat),
    ]
    poly_si = Polygon(ring_si)
    geoms35 = make_poly(3) + [MultiPolygon([poly_si])]
    gdf35 = gpd.GeoDataFrame({"geometry": geoms35}, geometry="geometry", crs="EPSG:4674")
    save_layer(gdf35, path, "AREA_ANTROPIZADA", overwrite=True)

    # TC-42/43: AREA_CONSOLIDADA — 8 bowtie records with known FIDs
    bowties = [shapely_wkt.loads(
        f"MULTIPOLYGON ((({-36+i*0.01} 0, {-36+i*0.01+0.01} 0.01, "
        f"{-36+i*0.01+0.01} 0, {-36+i*0.01} 0.01, {-36+i*0.01} 0)))"
    ) for i in range(8)]
    gdf_ac = gpd.GeoDataFrame({"geometry": bowties}, geometry="geometry", crs="EPSG:4674")
    save_layer(gdf_ac, path, "AREA_CONSOLIDADA", overwrite=True)

    log(f"B10 criada: {path}")
    log("  TC-43: abra AREA_CONSOLIDADA no QGIS e anote o FID dos bowties", "WARN")
    return path
    gdf_ac.to_file(path, layer="AREA_CONSOLIDADA", driver="GPKG",
                   engine="pyogrio", append=True)

    log(f"B10 criada: {path}")
    log("  TC-43: abra AREA_CONSOLIDADA no QGIS e anote o FID dos bowties", "WARN")
    return path

# ===========================================================================
# B11 — Performance base (100k+ valid records)
# ===========================================================================
def make_b11():
    import numpy as np
    path = out("B11_performance.gpkg")
    if os.path.exists(path): os.remove(path)

    N = 100_000
    log(f"B11: gerando {N:,} polígonos válidos...", "PROG")

    # Generate a grid of small polygons across RN bounding box
    # lon: -38.5 to -35.0  lat: -7.0 to -4.5
    lons = np.linspace(-38.5, -35.0, 320)
    lats = np.linspace(-7.0,  -4.5,  320)
    dx, dy = 0.009, 0.007

    geoms = []
    for lo in lons:
        for la in lats:
            if len(geoms) >= N:
                break
            ring = [(lo, la),(lo+dx, la),(lo+dx, la+dy),(lo, la+dy),(lo, la)]
            geoms.append(MultiPolygon([Polygon(ring)]))
        if len(geoms) >= N:
            break

    gdf = gpd.GeoDataFrame({"geometry": geoms[:N]},
                            geometry="geometry", crs="EPSG:4674")
    gdf.to_file(path, layer="VEGETACAO_ATUAL", driver="GPKG",
                engine="pyogrio", append=False)
    log(f"B11 criada: {path}  ({N:,} feições)")
    return path

# ===========================================================================
# B12 — Layer without geometry column
# ===========================================================================
def make_b12():
    path = out("B12_sem_geometria.gpkg")
    full_valid_base(path, skip_layers=["HIDROGRAFIA"])

    # Write HIDROGRAFIA as a plain pandas DataFrame (no geometry column).
    # pyogrio will write it as a non-spatial attribute table in the GeoPackage,
    # without registering a row in gpkg_geometry_columns.
    # When gpd.read_file() reads this layer it returns a plain DataFrame
    # (no .crs attribute), which is exactly the condition the validator checks.
    import pandas as pd
    df_no_geom = pd.DataFrame({"CLASSE": list(range(1, 9))})
    import pyogrio
    pyogrio.write_dataframe(df_no_geom, path, layer="HIDROGRAFIA",
                            driver="GPKG", append=True)

    log(f"B12 criada: {path}")
    log("  HIDROGRAFIA escrita como tabela sem geometria via pyogrio", "INFO")
    return path

# ===========================================================================
# Main
# ===========================================================================
def main():
    print()
    print("=" * 60)
    print("  SICAR AD — Criação das Bases de Teste para Homologação")
    print("=" * 60)
    print(f"  Diretório de saída: {OUT_DIR}")
    print()

    b01 = make_b01()

    try:
        make_b02()
    except Exception as e:
        log(f"B02 (GDB) não pôde ser criada: {e}", "WARN")
        log("  O driver OpenFileGDB para escrita requer o SDK ESRI ou GDAL >= 3.6.", "WARN")
        log("  Crie B02 manualmente no QGIS exportando B01 para GDB.", "WARN")

    make_b03(b01)
    make_b04()
    make_b05()
    make_b06()
    make_b07()
    make_b08()
    make_b09()
    make_b10()
    make_b11()
    make_b12()

    print()
    print("=" * 60)
    files = [f for f in os.listdir(OUT_DIR) if not f.startswith("_")]
    log(f"Total de arquivos gerados: {len(files)}")
    for f in sorted(files):
        size = os.path.getsize(os.path.join(OUT_DIR, f))
        sz = f"{size/1024:.0f} KB" if size < 1_048_576 else f"{size/1_048_576:.1f} MB"
        print(f"    {f:<45s} {sz:>8s}")
    print()
    log("Bases prontas para uso no plugin SICAR AD.")


if __name__ == "__main__":
    main()
