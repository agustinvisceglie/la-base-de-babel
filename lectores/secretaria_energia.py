"""
Secretaría de Energía (SE): descarga y lectura de los datos de producción de petróleo y gas.

Qué hace (lector: no convierte unidades, no agrupa, no suma, no elige variantes):
    - descargar_series_agregadas(): series oficiales "por cuenca y sub tipo de recurso (Capítulo IV)"
      de petróleo (m3 por mes) y de gas natural (miles de m3 por mes), con índice mensual.
    - descargar_pozos_no_convencional(): producción mensual por pozo de los pozos no convencionales.
    - descargar_pozos_anual(): producción mensual por pozo de un año, todos los pozos (para controles).
    - descargar_pozos_anual_ddjj(): ídem, variante "DDJJ abiertas y cerradas" (la fuente de Vaca Muerta).
    - versiones_pozos() y leer_pozos_version(): las versiones guardadas de un archivo por pozo (las
      usa la regla de la clasificación más reciente).
    - descargar_sesco_diaria(): producción promedio diaria por cuenca (SESCO), tal como viene. Solo controles.
    - revisar_portal() y autorizar_descarga(): antes de bajar, comparan la fecha de publicación del
      portal con la registrada; frenan si el portal no responde o si lo que cambió pasa 1 GB sin ok
      (regla 8 del instructivo). Ninguna función baja a ciegas.
    La descarga es condicional (comun/descargas.py, con la fecha de publicación del portal CKAN):
    baja solo si cambió y guarda solo la versión comprimida (sin copia "vigente"). Con
    actualizar.py --sin-descargar o --crudos-al no usa internet y lee las versiones registradas.
    Desde la raíz: .venv/Scripts/python -m lectores.secretaria_energia  (solo revisa el portal, no baja nada).

Fuente: portal de datos de la SE, datos.energia.gob.ar:
    - dataset "Producción de petróleo y gas por pozo (Capítulo IV)", ID c846e79c-026c-4040-897f-1ad3543b407c;
    - dataset "Producción de Petróleo y Gas (SESCO)", ID 590d1284-fd6d-4686-afd8-b3da5d90a6e9.
    El portal no publica un diccionario de campos: las unidades se verifican en los controles
    (bloques/energia/produccion.py) con las columnas diarias que calcula la propia SE.
Genera: las versiones de cada archivo en datos/crudos/secretaria_energia/versiones/ (comprimidas,
    con su registro en datos/registros/versiones_crudos.csv).
"""

from __future__ import annotations

import re

import pandas as pd
import requests

from comun import descargas as d
from comun.descargas import (CRUDOS, ENCABEZADOS, RAIZ, DescargaFrenada, autorizar_descarga,  # noqa: F401
                             descargar_condicional, revisar_http)

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
# Archivos anuales por pozo, variante "DDJJ abiertas y cerradas" (todos los pozos). Es la variante
# que reproduce la serie agregada de la SE: es la fuente de Vaca Muerta (criterios, sección 3).
RECURSOS_DDJJ_ABIERTAS_Y_CERRADAS = {
    2010: "8ee68ba4-2715-467c-af6f-233555520483", 2011: "da9d4417-2be6-4585-8f35-f2e8078c20e5",
    2012: "a6c391c5-4b88-4702-8080-72ba7106a02b", 2013: "158e5054-0c3b-478a-bbb7-f2d91c522e49",
    2014: "443d7488-1614-41bd-8dbd-82506e37e853", 2015: "36c4ca2b-8f9f-4bed-8ceb-ed9c8647f861",
    2016: "8a7f0dff-5a1d-4b1e-a8df-e566a85c3c69", 2017: "97c81dbc-9db4-4a61-8e78-ee0a934fa620",
    2018: "13e30415-a2ac-46fe-a8ff-9810d8323ac9", 2019: "d7dd85a5-4268-43b3-9ce5-c713cbbec2dc",
    2020: "508ce39a-00d0-4164-a997-7ad25dda1c1a", 2021: "cc966108-e577-4043-b553-81173ef83816",
    2022: "ae8d5a47-5181-4add-a836-ac19fb104fe1", 2023: "4b31fa79-dc2d-4228-a6ac-7e804cb36d1d",
    2024: "0a352dee-8b4e-4e95-b01e-5b8082ce22ac", 2025: "561279bf-1b7c-4fb1-9d39-9f3fb27ab237",
    2026: "85d6e021-a00d-4997-b74e-0b9b43c547fe",
}
POZOS_ANUAL_DDJJ = {
    anio: (f"produccion_pozos_{anio}_ddjj_abiertas_cerradas.csv",
           URL_CAPITULO_IV + f"{recurso}/download/produccin-de-pozos-de-gas-y-petrleo-{anio}-ddjj-abiertas-y-cerradas-.csv")
    for anio, recurso in RECURSOS_DDJJ_ABIERTAS_Y_CERRADAS.items()
}
SESCO_DIARIA = {
    "petroleo": ("sesco_petroleo_promedio_diario_cuenca.csv", URL_SESCO + "570015c9-fa8b-44a4-9bb6-02bd1b2c6c90/download/"
                 "produccin-de-petrleo-promedio-diaria-por-cuenca.csv"),
    "gas": ("sesco_gas_promedio_diario_cuenca.csv", URL_SESCO + "6a7866a1-723f-420c-898f-c482613646c5/download/"
            "produccin-de-gas-promedio-diaria-por-cuenca.csv"),
}

# Columnas de los archivos por pozo que se usan (el archivo trae 38 a 40).
COLUMNAS_POZOS = ["anio", "mes", "idpozo", "prod_pet", "prod_gas", "formprod", "tipo_de_recurso",
                  "sub_tipo_recurso", "cuenca", "areayacimiento", "fechaingreso"]
# Columnas de texto que se guardan como categorías (los archivos tienen ~1 millón de filas por año).
COLUMNAS_CATEGORIA = ["formprod", "tipo_de_recurso", "sub_tipo_recurso", "cuenca", "areayacimiento"]


def _recurso(url: str) -> str:
    return re.search(r"/resource/([0-9a-f-]{36})/", url).group(1)


def metadatos_portal(url: str) -> dict | None:
    """Fecha de última modificación y tamaño del recurso según la API del portal (CKAN,
    resource_show), o None si la API no responde o no informa la fecha. No baja el archivo."""
    try:
        respuesta = requests.get(f"http://datos.energia.gob.ar/api/3/action/resource_show?id={_recurso(url)}",
                                 headers=ENCABEZADOS, timeout=60)
        respuesta.raise_for_status()
        resultado = respuesta.json()["result"]
    except (requests.RequestException, KeyError, ValueError):
        return None
    if not resultado.get("last_modified"):
        return None
    return {"fecha_publicacion": resultado["last_modified"], "etag": None, "bytes": resultado.get("size"),
            "origen": "portal CKAN (last_modified)"}


def fecha_publicacion(url: str) -> str | None:
    """Fecha de última modificación del recurso según la API del portal (CKAN), o None si no responde."""
    metadatos = metadatos_portal(url)
    return metadatos["fecha_publicacion"] if metadatos else None


def _bajar(nombre: str, url: str, columnas: list[str] | None = None) -> tuple[pd.DataFrame, dict]:
    """Baja el archivo si cambió en el portal (si el portal no responde, frena: nunca a ciegas),
    guarda la versión y la lee (solo `columnas`, si se pasan)."""
    registro = descargar_condicional(url, "secretaria_energia", nombre, recurso=_recurso(url), obtener_metadatos=metadatos_portal)
    usar = (lambda c: c in columnas) if columnas else None
    tabla = pd.read_csv(RAIZ / registro["version"], encoding="utf-8-sig", low_memory=False, usecols=usar)  # traen BOM
    return tabla, registro


def revisar_portal(archivos: list[tuple[str, str]]) -> pd.DataFrame:
    """Sin bajar nada: para cada (nombre local, URL), qué cambió en el portal desde la última versión
    registrada y cuánto pesa (comun/descargas.revisar_http con los datos del portal CKAN)."""
    revision = revisar_http([("secretaria_energia", nombre, url) for nombre, url in archivos], obtener_metadatos=metadatos_portal)
    revision.insert(1, "recurso", [_recurso(url) for _, url in archivos])
    return revision


def archivos_produccion() -> list[tuple[str, str]]:
    """Todos los archivos de la SE que usa el armado de producción (series, por pozo y controles)."""
    return (list(SERIES_AGREGADAS.values()) + [POZOS_NO_CONVENCIONAL] + list(POZOS_ANUAL_DDJJ.values())
            + list(POZOS_ANUAL.values()) + list(SESCO_DIARIA.values()))


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
    for columna in COLUMNAS_CATEGORIA:
        tabla[columna] = tabla[columna].astype("category")
    tabla["fecha"] = pd.to_datetime(dict(year=tabla["anio"], month=tabla["mes"], day=1))
    return tabla


def versiones_pozos(nombre: str) -> list[dict]:
    """Versiones guardadas (distinto hash) de un archivo por pozo, según el registro de versiones:
    ruta de la copia, hash y fecha de publicación (si el portal republicó el mismo contenido, la
    más reciente). Con --crudos-al, solo las bajadas hasta ese momento. De la más vieja a la más nueva."""
    registro = d.leer_registro()
    filas = registro[registro["archivo"] == (CARPETA / nombre).relative_to(RAIZ).as_posix()]
    al = d._MODO["crudos_al"]
    if al:
        filas = filas[filas["fecha_descarga"].str[:len(al)] <= al]
    versiones = filas.groupby(["sha256", "version"], as_index=False)["fecha_publicacion"].max()
    return [{"ruta": RAIZ / v.version, "sha256": v.sha256, "fecha_publicacion": v.fecha_publicacion}
            for v in versiones.sort_values("fecha_publicacion").itertuples()]


def leer_pozos_version(ruta) -> pd.DataFrame:
    """Lee una versión guardada de un archivo por pozo (mismas columnas que las funciones de descarga)."""
    tabla = pd.read_csv(ruta, encoding="utf-8-sig", low_memory=False, usecols=lambda c: c in COLUMNAS_POZOS)
    return _leer_pozos(tabla)


def descargar_pozos_no_convencional() -> tuple[pd.DataFrame, dict]:
    """Producción mensual por pozo de los pozos no convencionales (prod_pet en m3, prod_gas en miles de m3)."""
    tabla, registro = _bajar(*POZOS_NO_CONVENCIONAL, columnas=COLUMNAS_POZOS)
    return _leer_pozos(tabla), registro


def descargar_pozos_anual(anio: int) -> tuple[pd.DataFrame, dict]:
    """Producción mensual por pozo de un año, todos los pozos (para controles)."""
    tabla, registro = _bajar(*POZOS_ANUAL[anio], columnas=COLUMNAS_POZOS)
    return _leer_pozos(tabla), registro


def descargar_pozos_anual_ddjj(anio: int) -> tuple[pd.DataFrame, dict]:
    """Producción mensual por pozo de un año, variante "DDJJ abiertas y cerradas", todos los pozos
    (prod_pet en m3, prod_gas en miles de m3)."""
    tabla, registro = _bajar(*POZOS_ANUAL_DDJJ[anio], columnas=COLUMNAS_POZOS)
    return _leer_pozos(tabla), registro


def descargar_sesco_diaria() -> tuple[dict[str, pd.DataFrame], list[dict]]:
    """SESCO: producción promedio diaria por cuenca, tal como viene (petróleo en m3/d y gas en miles
    de m3/d). Sumar las cuencas lo hace el armador."""
    tablas, registros = {}, []
    for clave, (nombre, url) in SESCO_DIARIA.items():
        tablas[clave], registro = _bajar(nombre, url)
        registros.append(registro)
    return tablas, registros


if __name__ == "__main__":
    # Solo revisa el portal: no baja ningún archivo.
    revision = revisar_portal(archivos_produccion())
    pd.set_option("display.width", 220)
    print(revision.to_string(index=False))
    a_bajar = revision[revision["estado"].isin(["cambió", "nuevo"])]
    sin_respuesta = revision[revision["estado"] == "sin respuesta"]
    print(f"\nCambiaron o son nuevos: {len(a_bajar)} de {len(revision)} "
          f"({a_bajar['bytes_a_bajar'].fillna(0).sum() / 1e9:.3f} GB). Sin respuesta del portal: {len(sin_respuesta)}.")
