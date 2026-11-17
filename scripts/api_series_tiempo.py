"""
API de Series de Tiempo de la República Argentina (apis.datos.gob.ar/series).

Qué hace:
    - descargar_series(): baja una o varias series por su ID y las devuelve como tabla
      (una fila por fecha, una columna por ID). Guarda el CSV original en datos/crudos/.
    - descargar_metadatos(): baja los metadatos de cada serie (título, unidad, frecuencia,
      dataset, organismo que la publica y fuente primaria) y los devuelve como tabla.

Fuente: https://apis.datos.gob.ar/series/api/series/ (documentación: https://datosgobar.github.io/series-tiempo-ar-api/)
    Para buscar IDs: https://apis.datos.gob.ar/series/api/search/?q=<palabras>
Genera: datos/crudos/api_series_tiempo/<nombre>.csv y <nombre>_metadatos.json
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.descargas import CRUDOS, RAIZ, descargar

URL_SERIES = "https://apis.datos.gob.ar/series/api/series/"
CARPETA = CRUDOS / "api_series_tiempo"


def descargar_series(ids: list[str], nombre: str, desde: str) -> tuple[pd.DataFrame, list[dict]]:
    """Baja las series `ids` desde la fecha `desde` (AAAA-MM-DD).

    Devuelve (tabla, registros_de_descarga). La tabla tiene como índice la fecha
    (primer día del período) y una columna por ID, con los valores tal como los publica la API.
    """
    # header=ids: las columnas del CSV vienen con el ID de cada serie (no dependen del orden).
    # limit=5000: máximo de filas que permite la API (alcanza para series mensuales desde 1900).
    url = (f"{URL_SERIES}?ids={','.join(ids)}&start_date={desde}"
           f"&limit=5000&format=csv&header=ids")
    registro = descargar(url, CARPETA / f"{nombre}.csv")

    tabla = pd.read_csv(RAIZ / registro["archivo"], parse_dates=["indice_tiempo"])
    tabla = tabla.rename(columns={"indice_tiempo": "fecha"}).set_index("fecha")

    faltantes = set(ids) - set(tabla.columns)
    if faltantes:
        raise ValueError(f"La API no devolvió estas series: {faltantes}")
    return tabla[ids], [registro]


def descargar_metadatos(ids: list[str], nombre: str) -> tuple[pd.DataFrame, list[dict]]:
    """Baja los metadatos de cada serie y devuelve una tabla con lo que hay que documentar."""
    filas, registros = [], []
    for id_serie in ids:
        url = f"{URL_SERIES}?ids={id_serie}&metadata=only"
        destino = CARPETA / f"{nombre}_metadatos_{id_serie}.json"
        registros.append(descargar(url, destino))
        meta = json.loads(Path(destino).read_text(encoding="utf-8"))["meta"]
        # meta[0] = frecuencia de la consulta; meta[1] = catálogo, dataset, distribución y serie
        info = meta[1]
        filas.append({
            "id": id_serie,
            "titulo": info["field"].get("title"),
            "descripcion": info["field"].get("description"),
            "unidades": info["field"].get("units"),
            "frecuencia": info["distribution"].get("frequency") or info["dataset"].get("accrualPeriodicity"),
            "dataset": info["dataset"].get("title"),
            "fuente_primaria": info["dataset"].get("source"),
            "publica": info["dataset"].get("publisher", {}).get("name"),
            "url_distribucion": info["distribution"].get("downloadURL"),
            "inicio": info["field"].get("time_index_start"),
            "fin_segun_metadatos": info["field"].get("time_index_end"),
        })
    return pd.DataFrame(filas), registros
