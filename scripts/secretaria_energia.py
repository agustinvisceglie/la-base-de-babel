"""
Secretaría de Energía (SE): descarga y lectura de los datos de producción de petróleo y gas.

Qué hace:
    - descargar_series_agregadas(): baja las series oficiales "por cuenca y sub tipo de recurso
      (Capítulo IV)" de petróleo (m3 por mes) y de gas natural (miles de m3 por mes).
    - descargar_pozos_no_convencional(): baja la producción mensual por pozo de los pozos no
      convencionales (Capítulo IV), con las columnas que se usan.
    - descargar_pozos_anual(): baja la producción mensual por pozo de un año, de todos los pozos.
      Se usa solo para controles (es un archivo de unos 250-330 MB por año).
    - descargar_sesco_diaria(): baja la producción promedio diaria por cuenca (SESCO). Solo para controles.

Fuente: portal de datos de la SE, datos.energia.gob.ar:
    - dataset "Producción de petróleo y gas por pozo (Capítulo IV)", ID c846e79c-026c-4040-897f-1ad3543b407c;
    - dataset "Producción de Petróleo y Gas (SESCO)", ID 590d1284-fd6d-4686-afd8-b3da5d90a6e9.
    El portal no publica un diccionario de campos: las unidades se verifican en los controles
    (series/produccion_hidrocarburos.py) con las columnas diarias que calcula la propia SE.
Genera: los archivos originales en datos/crudos/secretaria_energia/ (no se modifican) y una copia
    de cada versión distinta en datos/crudos/secretaria_energia/versiones/, con la fecha de
    publicación que informa el portal y el hash en el nombre (registro en datos/validacion/versiones_crudos.csv).
"""

from __future__ import annotations

import re

import pandas as pd
import requests

from scripts.descargas import CRUDOS, ENCABEZADOS, RAIZ, descargar, guardar_version

CARPETA = CRUDOS / "secretaria_energia"
URL_CAPITULO_IV = "http://datos.energia.gob.ar/dataset/c846e79c-026c-4040-897f-1ad3543b407c/resource/"
URL_SESCO = "http://datos.energia.gob.ar/dataset/590d1284-fd6d-4686-afd8-b3da5d90a6e9/resource/"

# (nombre local, URL del recurso tal como la publica el portal)
SERIES_AGREGADAS = {
    "petroleo": ("serie_petroleo_cuenca_subtipo.csv", URL_CAPITULO_IV + "af8c50bb-fde0-43b7-98eb-7cd14daf586c/download/"
                 "serie-histrica-de-produccin-de-petrleo-por-cuenca-y-sub-tipo-de-recurso-captulo-iv-.csv"),
    "gas": ("serie_gas_cuenca_subtipo.csv", URL_CAPITULO_IV + "a3244ddd-38bc-4800-a700-360b649d2f3a/download/"
            "serie-histrica-de-produccin-de-gas-natural-por-cuenca-y-sub-tipo-de-recurso-captulo-iv-.csv"),
}
POZOS_NO_CONVENCIONAL = ("produccion_pozos_no_convencional.csv", URL_CAPITULO_IV + "b5b58cdc-9e07-41f9-b392-fb9ec68b0725/download/"
                         "produccin-de-pozos-de-gas-y-petrleo-no-convencional.csv")
# Archivos anuales por pozo (todos los pozos). Solo se bajan los que se usan en controles. Si el
# portal tiene dos recursos para el mismo año, se usa el más reciente (criterio validado).
POZOS_ANUAL = {
    2015: ("produccion_pozos_2015.csv", URL_CAPITULO_IV + "e375aa35-fd8d-41d6-aa0c-e6879ca567a1/download/"
           "produccin-de-pozos-de-gas-y-petrleo-2015.csv"),
    2024: ("produccion_pozos_2024.csv", URL_CAPITULO_IV + "94d82d18-488b-434c-806d-ee5e053ce1cd/download/"
           "produccin-de-pozos-de-gas-y-petrleo-2024.csv"),   # el recurso más reciente de 2024 (18/11/2026)
    2026: ("produccion_pozos_2026.csv", URL_CAPITULO_IV + "fb7a47a0-cba9-4667-a004-6f6c1c346c23/download/"
           "produccin-de-pozos-de-gas-y-petrleo-2026.csv"),
}
SESCO_DIARIA = {
    "petroleo": ("sesco_petroleo_promedio_diario_cuenca.csv", URL_SESCO + "570015c9-fa8b-44a4-9bb6-02bd1b2c6c90/download/"
                 "produccin-de-petrleo-promedio-diaria-por-cuenca.csv"),
    "gas": ("sesco_gas_promedio_diario_cuenca.csv", URL_SESCO + "6a7866a1-723f-420c-898f-c482613646c5/download/"
            "produccin-de-gas-promedio-diaria-por-cuenca.csv"),
}

# Columnas de los archivos por pozo que se usan (el archivo trae 38 a 40).
COLUMNAS_POZOS = ["anio", "mes", "idpozo", "prod_pet", "prod_gas", "formprod", "tipo_de_recurso",
                  "sub_tipo_recurso", "cuenca", "fechaingreso"]


def fecha_publicacion(url: str) -> str | None:
    """Fecha de última modificación del recurso según la API del portal (CKAN), o None si no responde."""
    recurso = re.search(r"/resource/([0-9a-f-]{36})/", url).group(1)
    try:
        respuesta = requests.get(f"http://datos.energia.gob.ar/api/3/action/resource_show?id={recurso}",
                                 headers=ENCABEZADOS, timeout=60)
        respuesta.raise_for_status()
        return respuesta.json()["result"].get("last_modified")
    except (requests.RequestException, KeyError, ValueError):
        return None


def _bajar(nombre: str, url: str) -> tuple[pd.DataFrame, dict]:
    """Baja el archivo, guarda la versión (sin pisar las anteriores) y lo lee."""
    registro = guardar_version(descargar(url, CARPETA / nombre, timeout=600), fecha_publicacion(url))
    return pd.read_csv(RAIZ / registro["archivo"], encoding="utf-8-sig", low_memory=False), registro  # traen BOM


def _indice_mensual(tabla: pd.DataFrame, columna: str = "indice_tiempo") -> pd.DataFrame:
    tabla.index = pd.PeriodIndex(tabla.pop(columna), freq="M").to_timestamp()
    tabla.index.name = "fecha"
    return tabla


def descargar_series_agregadas() -> tuple[dict[str, pd.DataFrame], list[dict]]:
    """Series agregadas de petróleo y gas (índice = primer día del mes), tal como las publica la SE."""
    tablas, registros = {}, []
    for clave, (nombre, url) in SERIES_AGREGADAS.items():
        tabla, registro = _bajar(nombre, url)
        tablas[clave] = _indice_mensual(tabla)
        registros.append(registro)
    return tablas, registros


def _leer_pozos(tabla: pd.DataFrame) -> pd.DataFrame:
    tabla = tabla[COLUMNAS_POZOS].copy()
    tabla["fecha"] = pd.to_datetime(dict(year=tabla["anio"], month=tabla["mes"], day=1))
    return tabla


def descargar_pozos_no_convencional() -> tuple[pd.DataFrame, dict]:
    """Producción mensual por pozo de los pozos no convencionales (prod_pet en m3, prod_gas en miles de m3)."""
    tabla, registro = _bajar(*POZOS_NO_CONVENCIONAL)
    return _leer_pozos(tabla), registro


def descargar_pozos_anual(anio: int) -> tuple[pd.DataFrame, dict]:
    """Producción mensual por pozo de un año, todos los pozos (para controles)."""
    tabla, registro = _bajar(*POZOS_ANUAL[anio])
    return _leer_pozos(tabla), registro


def descargar_sesco_diaria() -> tuple[pd.DataFrame, list[dict]]:
    """SESCO: producción promedio diaria total del país (suma de cuencas), petróleo en m3/d y gas
    en miles de m3/d, tal como vienen."""
    columnas, registros = {}, []
    for clave, (nombre, url) in SESCO_DIARIA.items():
        tabla, registro = _bajar(nombre, url)
        valor = [c for c in tabla.columns if c.startswith("produccion_")][0]
        columnas[f"{clave}_{valor}"] = tabla.groupby("indice_tiempo")[valor].sum()
        registros.append(registro)
    tabla = pd.DataFrame(columnas).reset_index()
    return _indice_mensual(tabla), registros
