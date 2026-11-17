"""
INDEC: base de datos del Sistema de consulta de comercio exterior de bienes (comex.indec.gob.ar).

Qué hace:
    - descargar_base(): baja el zip anual con datos mensuales por posición NCM y país
      (exports_AAAA_M.zip o imports_AAAA_M.zip) a datos/crudos/indec_comex/.
    - sumar_capitulo(): suma, mes por mes, el valor de las posiciones de un capítulo de la NCM
      (exportaciones FOB o importaciones CIF), en millones de USD.

Advertencia (ver el "Léame" de cada zip): desde 2018 las exportaciones tienen secreto
estadístico. Las posiciones con pocos operadores se agrupan bajo el código 99999999
("Confidencial") y los valores por país aparecen como "s1" a "s10". Por eso la suma de un
capítulo puede quedar por debajo del total oficial. Las importaciones no tienen ese problema.

Fuente: INDEC, https://comex.indec.gob.ar/ (sección de descarga de bases de datos).
Genera: los zip originales en datos/crudos/indec_comex/ (no se modifican).
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd

from scripts.descargas import CRUDOS, descargar

URL_BASE = "https://comex.indec.gob.ar/files/zips/{flujo}_{anio}_M.zip"
CARPETA = CRUDOS / "indec_comex"


def descargar_base(flujo: str, anio: int) -> tuple[Path, dict]:
    """flujo: "exports" o "imports". Devuelve (ruta del zip, registro de la descarga)."""
    url = URL_BASE.format(flujo=flujo, anio=anio)
    destino = CARPETA / f"{flujo}_{anio}_M.zip"
    return destino, descargar(url, destino, timeout=300)


def sumar_capitulo(ruta_zip: Path, capitulo: str = "27") -> pd.Series:
    """Suma mensual de las posiciones NCM que empiezan con `capitulo`, en millones de USD.

    Exportaciones: valor FOB. Importaciones: valor CIF (el mismo criterio que el ICA).
    Los valores tapados por secreto estadístico ("s1" a "s10") quedan afuera de la suma.
    """
    with zipfile.ZipFile(ruta_zip) as archivo_zip:
        # Base principal: exponmAA.csv (desde 2018) o expomAA.csv (antes); impomAA.csv.
        nombre = next(n for n in archivo_zip.namelist()
                      if n.lower().endswith(".csv") and n.startswith(("exponm", "expom", "impom")))
        with archivo_zip.open(nombre) as archivo:
            base = pd.read_csv(archivo, sep=";", encoding="latin-1", dtype=str)

    base.columns = [c.strip() for c in base.columns]
    es_expo = nombre.startswith("expo")
    columna_valor = next(c for c in base.columns if c.startswith("FOB" if es_expo else "CIF"))
    columna_mes = next(c for c in base.columns if c.lower() == "mes")

    ncm = base["NCM"].str.strip()
    # Coma decimal; los valores confidenciales ("s2", etc.) se vuelven NaN y no suman.
    valor = pd.to_numeric(base[columna_valor].str.strip().str.replace(",", ".", regex=False), errors="coerce")
    mes = base[columna_mes].astype(int)
    return (valor[ncm.str.startswith(capitulo)].groupby(mes[ncm.str.startswith(capitulo)]).sum() / 1e6).rename("musd")
