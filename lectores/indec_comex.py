"""
INDEC: base de datos del Sistema de consulta de comercio exterior de bienes (comex.indec.gob.ar).

Qué hace:
    - descargar_base(): baja el zip anual con datos mensuales por posición NCM y país
      (exports_AAAA_M.zip o imports_AAAA_M.zip) a datos/crudos/indec_comex/.
    - leer_base(): lee la base principal del zip (posición NCM, mes y valor en USD, FOB en
      exportaciones y CIF en importaciones), como viene. Sumar por capítulo y convertir lo hace el armador.

Advertencia (ver el "Léame" de cada zip): desde 2018 las exportaciones tienen secreto
estadístico. Las posiciones con pocos operadores se agrupan bajo el código 99999999
("Confidencial") y los valores por país aparecen como "s1" a "s10". Por eso la suma de un
capítulo puede quedar por debajo del total oficial. Las importaciones no tienen ese problema.

Fuente: INDEC, https://comex.indec.gob.ar/ (sección de descarga de bases de datos).
Genera: las versiones de cada zip en datos/crudos/indec_comex/versiones/ (comprimidas, con su registro
    en datos/registros/versiones_crudos.csv). Descarga condicional por Last-Modified o ETag.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd

from comun.descargas import CRUDOS, RAIZ, descargar_condicional, leer_bytes

URL_BASE = "https://comex.indec.gob.ar/files/zips/{flujo}_{anio}_M.zip"
CARPETA = CRUDOS / "indec_comex"


def descargar_base(flujo: str, anio: int) -> tuple[Path, dict]:
    """flujo: "exports" o "imports". Baja el zip si cambió y devuelve (ruta de la versión guardada,
    registro de la descarga)."""
    url = URL_BASE.format(flujo=flujo, anio=anio)
    registro = descargar_condicional(url, "indec_comex", f"{flujo}_{anio}_M.zip")
    return RAIZ / registro["version"], registro


def leer_base(ruta_zip: Path) -> pd.DataFrame:
    """Lee la base principal del zip (exponmAA.csv desde 2018, expomAA.csv antes, o impomAA.csv) y
    devuelve una fila por registro con `ncm` (posición), `mes` y `valor_usd` (FOB en exportaciones,
    CIF en importaciones, el mismo criterio que el ICA). Los valores tapados por secreto estadístico
    ("s1" a "s10") quedan vacíos. Sumar por capítulo y convertir lo hace el armador.
    """
    with zipfile.ZipFile(leer_bytes(ruta_zip)) as archivo_zip:
        nombre = next(n for n in archivo_zip.namelist()
                      if n.lower().endswith(".csv") and n.startswith(("exponm", "expom", "impom")))
        with archivo_zip.open(nombre) as archivo:
            base = pd.read_csv(archivo, sep=";", encoding="latin-1", dtype=str)

    base.columns = [c.strip() for c in base.columns]
    es_expo = nombre.startswith("expo")
    columna_valor = next(c for c in base.columns if c.startswith("FOB" if es_expo else "CIF"))
    columna_mes = next(c for c in base.columns if c.lower() == "mes")
    # Coma decimal; los valores confidenciales ("s2", etc.) quedan vacíos (NaN).
    return pd.DataFrame({"ncm": base["NCM"].str.strip(), "mes": base[columna_mes].astype(int),
                         "valor_usd": pd.to_numeric(base[columna_valor].str.strip().str.replace(",", ".", regex=False), errors="coerce")})
