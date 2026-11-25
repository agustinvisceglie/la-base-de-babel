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
    - revisar_portal() y autorizar_descarga(): antes de bajar, comparan la fecha de publicación del
      portal con la registrada y frenan si el portal no responde (archivos sin verificar) o si lo
      que cambió pasa 1 GB sin ok (regla 8 del instructivo). Ninguna función baja a ciegas.
      Desde la raíz: .venv/Scripts/python -m scripts.secretaria_energia  (solo revisa, no baja nada).

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

from scripts.descargas import CRUDOS, ENCABEZADOS, RAIZ, REGISTRO_VERSIONES, descargar, guardar_version

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
# que reproduce la serie agregada de la SE (verificado en 2024): por el criterio validado ("la versión
# que coincida con la serie oficial"), es la fuente de Vaca Muerta. ID del recurso por año.
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


LIMITE_SIN_OK_BYTES = 1_000_000_000  # regla 8 del instructivo: más de 1 GB en total requiere el ok de Agustín


class DescargaFrenada(RuntimeError):
    """Se frena antes de bajar: el portal no informó la fecha de publicación de algún archivo
    (no se puede saber si cambió) o lo que hay que bajar supera el límite sin ok (regla 8)."""


def metadatos_portal(url: str) -> dict | None:
    """Fecha de última modificación y tamaño del recurso según la API del portal (CKAN,
    resource_show), o None si la API no responde. No baja el archivo."""
    recurso = re.search(r"/resource/([0-9a-f-]{36})/", url).group(1)
    try:
        respuesta = requests.get(f"http://datos.energia.gob.ar/api/3/action/resource_show?id={recurso}",
                                 headers=ENCABEZADOS, timeout=60)
        respuesta.raise_for_status()
        resultado = respuesta.json()["result"]
    except (requests.RequestException, KeyError, ValueError):
        return None
    if not resultado.get("last_modified"):
        return None
    return {"recurso": recurso, "fecha_publicacion": resultado["last_modified"], "bytes": resultado.get("size")}


def fecha_publicacion(url: str) -> str | None:
    """Fecha de última modificación del recurso según la API del portal (CKAN), o None si no responde."""
    metadatos = metadatos_portal(url)
    return metadatos["fecha_publicacion"] if metadatos else None


def _ultima_version(destino) -> pd.Series | None:
    """Última fila del registro de versiones de `destino` (la de fecha de publicación más reciente)."""
    if not REGISTRO_VERSIONES.exists():
        return None
    registro = pd.read_csv(REGISTRO_VERSIONES)
    filas = registro[registro["archivo"] == destino.relative_to(RAIZ).as_posix()]
    return filas.sort_values("fecha_publicacion").iloc[-1] if len(filas) else None


def revisar_portal(archivos: list[tuple[str, str]]) -> pd.DataFrame:
    """Sin bajar nada: compara, para cada (nombre local, URL), la fecha de publicación que informa
    el portal con la de la última versión registrada.

    estado: "sin cambios", "cambió", "nuevo" (no hay versión registrada) o "sin respuesta" (la API
    no respondió). bytes_a_bajar: el tamaño que informa el portal; si no responde, el de la última
    versión registrada (es lo que habría que volver a bajar para verificarlo)."""
    filas = []
    for nombre, url in archivos:
        ultima = _ultima_version(CARPETA / nombre)
        metadatos = metadatos_portal(url)
        registrada = None if ultima is None else ultima["fecha_publicacion"]
        bytes_local = None if ultima is None else int(ultima["bytes"])
        if metadatos is None:
            estado, publicada, tamanio = "sin respuesta", None, bytes_local
        else:
            publicada = metadatos["fecha_publicacion"]
            tamanio = int(metadatos["bytes"]) if metadatos["bytes"] else bytes_local
            estado = "nuevo" if registrada is None else ("sin cambios" if publicada == registrada else "cambió")
        filas.append({"archivo": nombre, "recurso": re.search(r"/resource/([0-9a-f-]{36})/", url).group(1),
                      "publicacion_registrada": registrada, "publicacion_portal": publicada, "estado": estado,
                      "bytes_registrados": bytes_local, "bytes_a_bajar": tamanio})
    return pd.DataFrame(filas)


def autorizar_descarga(revision: pd.DataFrame, ok_mas_de_1gb: bool = False) -> pd.DataFrame:
    """Frena (DescargaFrenada) si algún archivo quedó sin verificar porque el portal no respondió,
    o si lo que cambió supera 1 GB y no hay ok. Devuelve los archivos que hay que bajar."""
    sin_respuesta = revision[revision["estado"] == "sin respuesta"]
    if len(sin_respuesta):
        total = sin_respuesta["bytes_a_bajar"].fillna(0).sum()
        raise DescargaFrenada(
            "El portal no informó la fecha de publicación de estos archivos: quedan sin verificar y no se "
            f"vuelven a bajar sin el ok de Agustín ({total / 1e9:.2f} GB en total).\n"
            + sin_respuesta[["archivo", "recurso", "publicacion_registrada", "bytes_a_bajar"]].to_string(index=False))
    a_bajar = revision[revision["estado"].isin(["cambió", "nuevo"])]
    total = a_bajar["bytes_a_bajar"].fillna(0).sum()
    if total > LIMITE_SIN_OK_BYTES and not ok_mas_de_1gb:
        raise DescargaFrenada(
            f"Hay que bajar {total / 1e9:.2f} GB (más de 1 GB): falta el ok de Agustín (regla 8).\n"
            + a_bajar[["archivo", "publicacion_registrada", "publicacion_portal", "bytes_a_bajar"]].to_string(index=False))
    return a_bajar


def _version_registrada(destino, publicado: str) -> str | None:
    """Hash de la versión de `destino` registrada con esa fecha de publicación, o None."""
    if not REGISTRO_VERSIONES.exists():
        return None
    registro = pd.read_csv(REGISTRO_VERSIONES)
    filas = registro[(registro["archivo"] == destino.relative_to(RAIZ).as_posix()) & (registro["fecha_publicacion"] == publicado)]
    return filas["sha256"].iloc[-1] if len(filas) else None


def _bajar_archivo(nombre: str, url: str) -> dict:
    """Descarga condicional: si el portal informa la misma fecha de publicación que la última
    versión registrada y el archivo local es esa versión (mismo hash), no se baja de nuevo.
    Si no, se baja. En los dos casos se guarda la versión (sin pisar las anteriores).
    Si el portal no informa la fecha de publicación, frena (DescargaFrenada): nunca se baja a ciegas.
    El límite de 1 GB por corrida se controla antes, con revisar_portal() y autorizar_descarga()."""
    destino = CARPETA / nombre
    publicado = fecha_publicacion(url)
    if publicado is None:
        tamanio = destino.stat().st_size if destino.exists() else None
        raise DescargaFrenada(f"El portal no informó la fecha de publicación de {nombre} (recurso de {url}); "
                              f"queda sin verificar y no se vuelve a bajar sin el ok de Agustín "
                              f"(tamaño local: {tamanio if tamanio is not None else 'no hay copia local'} bytes).")
    registro = None
    if destino.exists():
        hash_registrado = _version_registrada(destino, publicado)
        if hash_registrado:
            local = descargar(url, destino, reusar_si_existe=True)  # no baja: calcula el hash del archivo local
            if local["sha256"] == hash_registrado:
                registro = local
    if registro is None:
        registro = descargar(url, destino, timeout=600)
    return guardar_version(registro, publicado)


def _bajar(nombre: str, url: str, columnas: list[str] | None = None) -> tuple[pd.DataFrame, dict]:
    """Baja el archivo (si cambió en el portal), guarda la versión y lo lee (solo `columnas`, si se pasan)."""
    registro = _bajar_archivo(nombre, url)
    usar = (lambda c: c in columnas) if columnas else None
    tabla = pd.read_csv(RAIZ / registro["archivo"], encoding="utf-8-sig", low_memory=False, usecols=usar)  # traen BOM
    return tabla, registro


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
    más reciente). Ordenadas de la más vieja a la más nueva."""
    registro = pd.read_csv(REGISTRO_VERSIONES)
    filas = registro[registro["archivo"] == (CARPETA / nombre).relative_to(RAIZ).as_posix()]
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


def archivos_produccion() -> list[tuple[str, str]]:
    """Todos los archivos de la SE que usa el armado de producción (series, por pozo y controles)."""
    return (list(SERIES_AGREGADAS.values()) + [POZOS_NO_CONVENCIONAL] + list(POZOS_ANUAL_DDJJ.values())
            + list(POZOS_ANUAL.values()) + list(SESCO_DIARIA.values()))


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


if __name__ == "__main__":
    # Solo revisa el portal: no baja ningún archivo.
    revision = revisar_portal(archivos_produccion())
    pd.set_option("display.width", 220)
    print(revision.to_string(index=False))
    a_bajar = revision[revision["estado"].isin(["cambió", "nuevo"])]
    sin_respuesta = revision[revision["estado"] == "sin respuesta"]
    print(f"\nCambiaron o son nuevos: {len(a_bajar)} de {len(revision)} "
          f"({a_bajar['bytes_a_bajar'].fillna(0).sum() / 1e9:.3f} GB). Sin respuesta del portal: {len(sin_respuesta)}.")
