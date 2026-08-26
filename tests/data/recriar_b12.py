# -*- coding: utf-8 -*-
"""Recreates only the B12 test base with a correct geometry-less HIDROGRAFIA layer."""
import os, sys
import geopandas as gpd
import pandas as pd
from shapely.geometry import MultiPolygon, Polygon

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR    = os.path.join(SCRIPT_DIR, "bases_teste")  # tests/data/bases_teste/

def out(name):
    return os.path.join(OUT_DIR, name)

LAYERS_WITH_CLASSE = {
    "HIDROGRAFIA":  (1, 8),
    "APP":          (1, 8),
    "SERVIDAO":     (1, 4),
    "RELEVO":       (1, 8),
    "USO_RESTRITO": (1, 2),
    "APP_ESPECIAL": (1, 10),
}
LAYERS_WITHOUT_CLASSE = [
    "AREA_ANTROPIZADA", "AREA_CONSOLIDADA", "VEGETACAO_ATUAL", "VEGETACAO_2008",
]
ALL_LAYERS = LAYERS_WITHOUT_CLASSE + list(LAYERS_WITH_CLASSE.keys())

_offset = 0.0
def make_poly(n=1):
    global _offset
    geoms = []
    for i in range(n):
        lon = -37.0 - _offset - i * 0.01
        lat = -6.0  - _offset - i * 0.01
        ring = [(lon,lat),(lon+0.005,lat),(lon+0.005,lat+0.005),(lon,lat+0.005),(lon,lat)]
        geoms.append(MultiPolygon([Polygon(ring)]))
    _offset += 0.001
    return geoms

def save_layer(gdf, path, layer):
    mode = "w" if not os.path.exists(path) else "a"
    gdf.to_file(path, layer=layer, driver="GPKG", engine="pyogrio", mode=mode)

path = out("B12_sem_geometria.gpkg")

# Remove existing file
if os.path.exists(path):
    try:
        os.remove(path)
        print(f"[OK] Arquivo anterior removido.")
    except PermissionError:
        print("[ERRO] Feche o arquivo B12 no QGIS antes de continuar.")
        sys.exit(1)

# Write all layers except HIDROGRAFIA with geometry
for layer in ALL_LAYERS:
    if layer == "HIDROGRAFIA":
        continue
    if layer in LAYERS_WITH_CLASSE:
        lo, hi = LAYERS_WITH_CLASSE[layer]
        gdf = gpd.GeoDataFrame(
            {"geometry": make_poly(hi-lo+1), "CLASSE": list(range(lo, hi+1))},
            geometry="geometry", crs="EPSG:4674")
    else:
        gdf = gpd.GeoDataFrame({"geometry": make_poly(3)}, geometry="geometry", crs="EPSG:4674")
    save_layer(gdf, path, layer)

# Write HIDROGRAFIA as a plain DataFrame (no geometry column)
# pyogrio writes it as a non-spatial attribute table — gpd.read_file returns
# a plain DataFrame without .crs, which is the condition the validator tests.
df_no_geom = pd.DataFrame({"CLASSE": list(range(1, 9))})
import pyogrio
pyogrio.write_dataframe(df_no_geom, path, layer="HIDROGRAFIA",
                        driver="GPKG", append=True)

# Verify
import pyogrio as _p
layers = _p.list_layers(path)
print(f"\n[OK] B12 recriada: {path}")
print(f"     Camadas: {[l[0] for l in layers]}")

# Check that HIDROGRAFIA has no geometry type
for lname, lgeom in layers:
    if lname == "HIDROGRAFIA":
        print(f"     HIDROGRAFIA geometry_type: '{lgeom}' (deve estar vazio/None)")
