"""
Bloque 1, sector externo: comercio exterior de bienes (Intercambio comercial argentino, ICA, del INDEC).

Qué hace (criterios, sección 1; migrado de la nota "La vuelta del gas" en el Paso 3b):
    1. ica_mensual: exportaciones e importaciones totales, Combustibles y energía (CyE),
       Combustibles y lubricantes (CyL) y saldo comercial de bienes, mensual desde enero de 2004,
       de la serie oficial por rubros y usos (serie_rubros_usos_mensual.xlsx) de la versión
       interactiva del informe más reciente. No se derivan ni se estiman meses. Llega hasta el mes
       de ese informe (el último mes completo de la fuente); el corte de cada nota lo pone la nota.
    2. ica_anual: anual oficial (cuadros anuales por rubro y uso, desde 1980) y, como control, el
       capítulo 27 de la NCM (cuadros anuales por capítulo; para cada año, el más reciente; antes de
       2010, suma de los 12 meses de la API de Series de Tiempo).
    3. ica_cap27_mensual (control): capítulo 27 mensual, derivado de los acumulados oficiales de
       cada informe (y de la API para los meses anteriores a esos informes).
    4. ica_acumulados_informes: los acumulados oficiales del año (enero al mes del informe) que
       publica cada informe usado, del año en curso y del anterior: cuadro 1 (totales y saldo de
       bienes), cuadros de rubros y usos (CyE y CyL) y cuadro del capítulo 27. Sirven para citar
       acumulados y primeras publicaciones sin sumar meses.
    5. Controles y validación (datos/validacion/sector_externo/): lo leído contra lo publicado en
       el PDF; la serie mensual contra los anuales y los acumulados oficiales; unidades de los
       cuadros por capítulo; capítulo 27 (suma de meses, API, publicado vs. derivado, anual vs.
       informes de diciembre) y capítulo 27 en la base comex del INDEC vs. lo oficial.
    Las conversiones de unidades se hacen acá: los lectores devuelven lo que publica la fuente.

Fuentes (todas del INDEC; lector: lectores/indec.py, lectores/api_series_tiempo.py y lectores/indec_comex.py):
    - Informes técnicos del ICA: listado oficial (https://www.indec.gob.ar/Institucional/Indec/InformesTecnicos/40),
      Excel de cuadros de cada informe (ica_cuadros_DD_MM_AA.xls) y versión interactiva.
    - Cuadros anuales: exp_gr_80_AA.xls e imp_uso_econ_80_AA.xls (rubros y usos), exp_ncm_AA_AA.xls e
      imp_ncm_AA_AA.xls (capítulos de la NCM, quinquenios desde 2010-2014).
    - API de Series de Tiempo (SSPM, fuente INDEC): 162.3_XMB_MINION_0_0_56 y 163.3_MMBUSTIION_0_0_59.
    - Base del Sistema de consulta de comercio exterior (comex.indec.gob.ar): exports/imports_AAAA_M.zip.

Genera (lo escribe actualizar.py): datos/series/sector_externo/*.csv y datos/validacion/sector_externo/*.csv.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from lectores import api_series_tiempo, indec, indec_comex

DESDE = "2004-01-01"  # comienzo de la serie mensual oficial por rubros y usos
PRIMER_ANIO_CONTRASTE = 2022  # primera publicación vs. vigente, desde este año (auditoría de la etapa 1)
SERIES_API_CAP27 = {"162.3_XMB_MINION_0_0_56": "expo_cap27_musd", "163.3_MMBUSTIION_0_0_59": "impo_cap27_musd"}
FUENTE_API = "API Series de Tiempo (INDEC; publica SSPM)"
ARCHIVOS_PAGINA_ICA = {"expo_anual_rubros": "exp_gr_80_", "impo_anual_usos": "imp_uso_econ_80_",
                       "expo_anual_capitulos": "exp_ncm_", "impo_anual_capitulos": "imp_ncm_"}
# Cuadros anuales por capítulo de quinquenios anteriores (siguen en el servidor, ya no se enlazan).
QUINQUENIOS_CAPITULOS = ["10_14", "12_16", "13_17", "14_18", "15_19", "16_20", "17_21", "18_22", "19_23", "20_24"]
# Años de la base comex para el control del capítulo 27: dos anteriores al secreto estadístico (2018) y varios posteriores.
ANIOS_COMEX = [2006, 2015, 2018, 2020, 2022, 2024, 2025]
TOLERANCIA_MUSD = 1.0  # los informes redondean a millones enteros

# Valores publicados en el PDF de los informes, para contrastar con lo leído de los Excel de cuadros.
# (dato, fecha de publicación del informe, cuadro leído, claves, valor publicado, dónde)
CONTROLES_PUBLICADOS = [
    ("Exportación CyE, sep-2026", "2026-10-19", "rubros_usos", ("mes_actual", "expo_cye"), 1781,
     "Informe ICA de septiembre 2026 (19/10/2026), p. 9 (texto: 'USD 1.781 millones')"),
    ("Exportación CyE, acum. ene-sep 2026", "2026-10-19", "rubros_usos", ("acumulado", "actual", "expo_cye"), 12452,
     "Ídem, p. 6 (gráfico 'Exportaciones por grandes rubros e importaciones por usos económicos', acumulado)"),
    ("Importación CyL, acum. ene-sep 2026", "2026-10-19", "rubros_usos", ("acumulado", "actual", "impo_cyl"), 3025, "Ídem, p. 6"),
    ("Exportaciones totales, acum. ene-sep 2026", "2026-10-19", "cuadro1", ("actual", "expo"), 77267,
     "Informe ICA de septiembre 2026 (19/10/2026), p. 7, cuadro 1"),
    ("Importaciones totales, acum. ene-sep 2026", "2026-10-19", "cuadro1", ("actual", "impo"), 56069, "Ídem"),
    ("Saldo comercial de bienes, acum. ene-sep 2026", "2026-10-19", "cuadro1", ("actual", "saldo"), 21198, "Ídem"),
    ("Saldo comercial de bienes, acum. ene-sep 2025", "2026-10-19", "cuadro1", ("anterior", "saldo"), 6046, "Ídem"),
    ("Saldo cap. 27, acum. ene-dic 2025 (versión de enero 2026)", "2026-01-20", "cap27", ("acumulado", "actual", "saldo"), 6663,
     "Informe ICA de diciembre 2025 (20/01/2026), cuadro del capítulo 27"),
    ("Saldo cap. 27, acum. ene-ago 2026", "2026-09-18", "cap27", ("acumulado", "actual", "saldo"), 6576,
     "Informe ICA de agosto 2026 (18/09/2026), p. 28, cuadro 8"),
    ("Exportación cap. 27, sep-2026", "2026-10-19", "cap27", ("mes_actual", "expo"), 1586,
     "Informe ICA de septiembre 2026 (19/10/2026), p. 28, cuadro 8"),
    ("Importación cap. 27, sep-2026", "2026-10-19", "cap27", ("mes_actual", "impo"), 146, "Ídem"),
    ("Saldo cap. 27, sep-2026", "2026-10-19", "cap27", ("mes_actual", "saldo"), 1441, "Ídem"),
    ("Saldo cap. 27, sep-2025 (revisado)", "2026-10-19", "cap27", ("mes_anterior", "saldo"), 692, "Ídem"),
    ("Exportación cap. 27, acum. ene-sep 2026", "2026-10-19", "cap27", ("acumulado", "actual", "expo"), 10787, "Ídem"),
    ("Importación cap. 27, acum. ene-sep 2026", "2026-10-19", "cap27", ("acumulado", "actual", "impo"), 2787, "Ídem"),
    ("Saldo cap. 27, acum. ene-sep 2026", "2026-10-19", "cap27", ("acumulado", "actual", "saldo"), 8000, "Ídem"),
    ("Saldo cap. 27, acum. ene-sep 2025 (revisado)", "2026-10-19", "cap27", ("acumulado", "anterior", "saldo"), 4503, "Ídem"),
]

# ---------------------------------------------------------------------------------------------
# Declaración de series (de acá sale el catálogo)
# ---------------------------------------------------------------------------------------------
INFORME_VALIDACION = "datos/validacion/sector_externo/informe_validacion.md"
URL_INFORMES = "https://www.indec.gob.ar/Institucional/Indec/InformesTecnicos/40"
URL_PAGINA = "https://www.indec.gob.ar/Nivel4/Tema/3/2/40"
UNIDAD = "millones de USD corrientes (exportaciones FOB, importaciones CIF)"
UNIDAD_ACUMULADO = "millones de USD corrientes, acumulado de enero al mes del informe"


def _serie(archivo, columna, nombre, tipo="nivel", frecuencia="mensual", uso="base", unidad=UNIDAD, fuente_id="", fuente_url=URL_INFORMES,
           lector="lectores/indec.py", criterio="§1 Balanza comercial energética (fuente: ICA del INDEC)"):
    return {"archivo": archivo, "columna": columna, "nombre": nombre, "unidad": unidad, "frecuencia": frecuencia, "tipo": tipo,
            "precios": "corrientes", "ajuste_estacional": "original", "uso": uso, "organismo": "INDEC", "rotulo": "oficial",
            "fuente_id": fuente_id, "fuente_url": fuente_url, "lector": lector, "criterio": criterio, "estimados": "no",
            "tiene_revisiones": "sí: el INDEC revisa los meses y años recientes (ver la validación)",
            "discontinuada": "no", "con_reservas": "no", "informe_validacion": INFORME_VALIDACION}


_MENSUAL = "serie_rubros_usos_mensual.xlsx de la versión interactiva del informe más reciente del ICA"
_ANUAL = "exp_gr_80_AA.xls e imp_uso_econ_80_AA.xls (cuadros anuales por rubro y uso)"
_CAP27_ANUAL = "exp_ncm_AA_AA.xls e imp_ncm_AA_AA.xls (cuadros anuales por capítulo); antes de 2010, suma de meses de la API"
_CAP27_MENSUAL = ("acumulados del cuadro del capítulo 27 de cada informe del ICA (ica_cuadros_DD_MM_AA.xls) y API de Series "
                  "de Tiempo 162.3_XMB_MINION_0_0_56 y 163.3_MMBUSTIION_0_0_59")
_ACUM = "Excel de cuadros de cada informe del ICA (ica_cuadros_DD_MM_AA.xls)"
_CRITERIO_CAP27 = "§1: el capítulo 27 queda solo como control"

SERIES = [
    _serie("ica_mensual.csv", "expo_total_musd", "Exportaciones totales de bienes", fuente_id=_MENSUAL),
    _serie("ica_mensual.csv", "expo_cye_musd", "Exportaciones de Combustibles y energía (CyE)", fuente_id=_MENSUAL),
    _serie("ica_mensual.csv", "impo_total_musd", "Importaciones totales de bienes", fuente_id=_MENSUAL),
    _serie("ica_mensual.csv", "impo_cyl_musd", "Importaciones de Combustibles y lubricantes (CyL)", fuente_id=_MENSUAL),
    _serie("ica_mensual.csv", "saldo_total_musd", "Saldo comercial de bienes", tipo="saldo", fuente_id=_MENSUAL),
    _serie("ica_anual.csv", "expo_total_musd", "Exportaciones totales de bienes, anual", frecuencia="anual", fuente_id=_ANUAL, fuente_url=URL_PAGINA),
    _serie("ica_anual.csv", "impo_total_musd", "Importaciones totales de bienes, anual", frecuencia="anual", fuente_id=_ANUAL, fuente_url=URL_PAGINA),
    _serie("ica_anual.csv", "expo_cye_musd", "Exportaciones de CyE, anual", frecuencia="anual", fuente_id=_ANUAL, fuente_url=URL_PAGINA),
    _serie("ica_anual.csv", "impo_cyl_musd", "Importaciones de CyL, anual", frecuencia="anual", fuente_id=_ANUAL, fuente_url=URL_PAGINA),
    _serie("ica_anual.csv", "saldo_total_musd", "Saldo comercial de bienes, anual", tipo="saldo", frecuencia="anual", fuente_id=_ANUAL, fuente_url=URL_PAGINA),
    _serie("ica_anual.csv", "expo_cap27_musd", "Exportaciones del capítulo 27 de la NCM, anual (control)", frecuencia="anual", uso="control",
           fuente_id=_CAP27_ANUAL, fuente_url=URL_PAGINA, criterio=_CRITERIO_CAP27),
    _serie("ica_anual.csv", "impo_cap27_musd", "Importaciones del capítulo 27 de la NCM, anual (control)", frecuencia="anual", uso="control",
           fuente_id=_CAP27_ANUAL, fuente_url=URL_PAGINA, criterio=_CRITERIO_CAP27),
    _serie("ica_anual.csv", "saldo_cap27_musd", "Saldo del capítulo 27 de la NCM, anual (control)", tipo="saldo", frecuencia="anual", uso="control",
           fuente_id=_CAP27_ANUAL, fuente_url=URL_PAGINA, criterio=_CRITERIO_CAP27),
    _serie("ica_cap27_mensual.csv", "expo_cap27_musd", "Exportaciones del capítulo 27 de la NCM (control)", uso="control", fuente_id=_CAP27_MENSUAL, criterio=_CRITERIO_CAP27),
    _serie("ica_cap27_mensual.csv", "impo_cap27_musd", "Importaciones del capítulo 27 de la NCM (control)", uso="control", fuente_id=_CAP27_MENSUAL, criterio=_CRITERIO_CAP27),
    _serie("ica_cap27_mensual.csv", "saldo_cap27_musd", "Saldo del capítulo 27 de la NCM (control)", tipo="saldo", uso="control", fuente_id=_CAP27_MENSUAL, criterio=_CRITERIO_CAP27),
]
for _prefijo, _anio in (("acum", "del año del informe"), ("acum_ant", "del año anterior, mismo período")):
    for _col, _nombre, _tipo, _uso in (("expo_total_musd", "Exportaciones totales (cuadro 1)", "nivel", "base"),
                                       ("impo_total_musd", "Importaciones totales (cuadro 1)", "nivel", "base"),
                                       ("saldo_total_musd", "Saldo comercial de bienes (cuadro 1)", "saldo", "base"),
                                       ("expo_cye_musd", "Exportaciones de CyE (cuadro de rubros)", "nivel", "base"),
                                       ("impo_cyl_musd", "Importaciones de CyL (cuadro de usos)", "nivel", "base"),
                                       ("expo_cap27_musd", "Exportaciones del capítulo 27 (control)", "nivel", "control"),
                                       ("impo_cap27_musd", "Importaciones del capítulo 27 (control)", "nivel", "control"),
                                       ("saldo_cap27_musd", "Saldo del capítulo 27 (control)", "saldo", "control")):
        SERIES.append(_serie("ica_acumulados_informes.csv", f"{_prefijo}_{_col}", f"{_nombre}: acumulado oficial {_anio}, según cada informe",
                             tipo=_tipo, uso=_uso, unidad=UNIDAD_ACUMULADO, fuente_id=_ACUM,
                             criterio=_CRITERIO_CAP27 if _uso == "control" else "§1 Balanza comercial energética (fuente: ICA del INDEC)"))
del _prefijo, _anio, _col, _nombre, _tipo, _uso

AUXILIARES = {
    "ica_anual.csv": ["provisorio", "fuente_cap27", "archivo_expo_rubros", "archivo_impo_usos"],
    "ica_cap27_mensual.csv": ["fuente"],
    "ica_acumulados_informes.csv": ["mes_informe", "archivo", "hoja_expo", "hoja_impo"],
}
FORMATO = {archivo: "%.8f" for archivo in ("ica_mensual.csv", "ica_anual.csv", "ica_cap27_mensual.csv", "ica_acumulados_informes.csv")}  # la fuente trae centavos de USD: 8 decimales en millones


# ---------------------------------------------------------------------------------------------
# 1. Lectura (con los lectores)
# ---------------------------------------------------------------------------------------------
def leer() -> dict:
    """Baja (si cambió) y lee todo lo necesario. Devuelve las tablas leídas y los registros."""
    registros = []
    api, regs = api_series_tiempo.descargar_series(list(SERIES_API_CAP27), "cap27_mensual", DESDE)
    registros += regs
    metadatos, regs = api_series_tiempo.descargar_metadatos(list(SERIES_API_CAP27), "cap27_mensual")
    registros += regs
    api = api.rename(columns=SERIES_API_CAP27).dropna()

    urls, regs = indec.buscar_archivos(indec.PAGINA_ICA, list(ARCHIVOS_PAGINA_ICA.values()), "pagina_ica.html")
    registros += regs
    rutas, nombres = {}, {}
    for clave, prefijo in ARCHIVOS_PAGINA_ICA.items():
        rutas[clave], registro = indec.descargar_archivo(urls[prefijo])
        nombres[clave] = Path(registro["archivo"]).name
        registros.append(registro)
    capitulos = {"expo": [], "impo": []}  # (ruta, nombre), del cuadro más viejo al más nuevo
    for quinquenio in QUINQUENIOS_CAPITULOS:
        for flujo, prefijo in (("expo", "exp"), ("impo", "imp")):
            ruta, registro = indec.descargar_archivo(f"{indec.URL_INDEC}/ftp/cuadros/economia/{prefijo}_ncm_{quinquenio}.xls")
            capitulos[flujo].append((ruta, Path(registro["archivo"]).name))
            registros.append(registro)
    capitulos["expo"].append((rutas["expo_anual_capitulos"], nombres["expo_anual_capitulos"]))
    capitulos["impo"].append((rutas["impo_anual_capitulos"], nombres["impo_anual_capitulos"]))

    informes_todos, regs = indec.listar_informes_ica("listado_informes_ica.html")
    registros += regs
    # Informes del capítulo 27 mensual: desde el mes siguiente al último dato de la API.
    primer_informe = api.index.max() + pd.DateOffset(months=1)
    informes = informes_todos[informes_todos["fecha_publicacion"] >= primer_informe].reset_index(drop=True)
    cuadros = [leer_cuadros(informe, registros) for informe in informes.itertuples()]
    ultimo = max(cuadros, key=lambda c: c["fecha_publicacion"])
    informes = informes.copy()
    informes["mes_del_informe"] = [c["rubros_usos"]["mes"].strftime("%Y-%m") for c in cuadros]

    # Informes de diciembre (salen en enero) para la primera publicación y la revisión de cada año.
    anio_completo = ultimo["rubros_usos"]["mes"].year - 1
    en_ventana = {c["fecha_publicacion"] for c in cuadros}
    de_enero = []
    for anio_publicacion in range(PRIMER_ANIO_CONTRASTE + 1, anio_completo + 3):
        candidatos = informes_todos[(informes_todos["fecha_publicacion"].dt.year == anio_publicacion)
                                    & (informes_todos["fecha_publicacion"].dt.month == 1)]
        if candidatos.empty:
            continue
        informe = candidatos.iloc[0]
        if informe.fecha_publicacion in en_ventana:
            de_enero.append(next(c for c in cuadros if c["fecha_publicacion"] == informe.fecha_publicacion))
        else:
            de_enero.append(leer_cuadros(informe, registros, capitulo27_opcional=True))

    ruta_rubros, registro = indec.descargar_archivo(ultimo["url_interactivo"] + "data/cuadros/serie_rubros_usos_mensual.xlsx")
    registros.append(registro)
    return {"api": api, "metadatos": metadatos, "rutas": rutas, "nombres": nombres, "capitulos": capitulos,
            "informes": informes, "cuadros": cuadros, "de_enero": de_enero, "ultimo": ultimo,
            "rubros_usos_largo": indec.leer_rubros_usos_mensual(ruta_rubros), "registros": registros}


def leer_cuadros(informe, registros: list, capitulo27_opcional: bool = False) -> dict:
    """Lee del Excel de cuadros de un informe el cuadro 1, los de rubros y usos y el del capítulo 27."""
    ruta, registro = indec.descargar_archivo(informe.url_cuadros)
    registros.append(registro)
    cuadro = {"fecha_publicacion": informe.fecha_publicacion, "url_interactivo": informe.url_interactivo,
              "archivo": Path(registro["archivo"]).name,
              "cuadro1": indec.leer_cuadro1_acumulado(ruta), "rubros_usos": indec.leer_cuadro_rubros_usos(ruta)}
    try:
        cuadro["cap27"] = indec.leer_cuadro_capitulo27(ruta)
    except (ValueError, StopIteration):
        if not capitulo27_opcional:
            raise
        cuadro["cap27"] = None  # algunos informes viejos no traen el cuadro del capítulo 27
    meses = {cuadro["rubros_usos"]["mes"], cuadro["cuadro1"]["mes"]} | ({cuadro["cap27"]["mes"]} if cuadro["cap27"] else set())
    if len(meses) != 1:
        raise ValueError(f"{cuadro['archivo']}: el cuadro 1, el de rubros y usos y el del capítulo 27 son de meses distintos")
    return cuadro


# ---------------------------------------------------------------------------------------------
# 2. Series
# ---------------------------------------------------------------------------------------------
def armar_ica_mensual(largo: pd.DataFrame, ultimo_mes: pd.Timestamp) -> pd.DataFrame:
    """Totales, CyE, CyL y saldo comercial mensuales, en millones de USD, hasta el mes del último
    informe. Los totales son la suma de todos los rubros o usos (incluido "Resto")."""
    largo = largo.copy()
    largo["valor"] = largo["valor"] / 1e6  # USD -> millones de USD
    expo = largo[largo["comercio"] == "Exportaciones"]
    impo = largo[largo["comercio"] == "Importaciones"]
    es_cye = expo["rubro_uso"].str.startswith("Combustibles y energía")
    es_cyl = impo["rubro_uso"].str.startswith("Combustibles y lubricantes")
    ica = pd.DataFrame({
        "expo_total_musd": expo.groupby("fecha")["valor"].sum(),
        "expo_cye_musd": expo[es_cye].groupby("fecha")["valor"].sum(),
        "impo_total_musd": impo.groupby("fecha")["valor"].sum(),
        "impo_cyl_musd": impo[es_cyl].groupby("fecha")["valor"].sum(),
    }).loc[:ultimo_mes]
    ica.index.name = "fecha"
    ica["saldo_total_musd"] = ica["expo_total_musd"] - ica["impo_total_musd"]
    return ica


def armar_anual(rutas: dict, nombres: dict, capitulos: dict, cap27_mensual: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Anual oficial: totales, CyE, CyL y capítulo 27 (revisión más reciente de cada año). Devuelve
    también el control de unidades de los cuadros por capítulo: el "Total" de cada cuadro tiene que
    parecerse al total anual oficial (cociente entre 0,8 y 1,25); si un cuadro viniera en miles en
    vez de millones, daría 1.000."""
    expo = indec.leer_ica_anual(rutas["expo_anual_rubros"], "Combustibles y energía")
    impo = indec.leer_ica_anual(rutas["impo_anual_usos"], "Combustibles y lubricantes")
    anual = pd.DataFrame({
        "expo_total_musd": expo["total"] / 1000, "impo_total_musd": impo["total"] / 1000,   # miles -> millones de USD
        "expo_cye_musd": expo["rubro"] / 1000, "impo_cyl_musd": impo["rubro"] / 1000,
    })
    anual["saldo_total_musd"] = anual["expo_total_musd"] - anual["impo_total_musd"]
    anual["provisorio"] = expo["provisorio"] | impo["provisorio"]

    cap27, archivo, unidades = {"expo": {}, "impo": {}}, {}, []
    for flujo in ("expo", "impo"):
        for ruta, nombre in capitulos[flujo]:
            cuadro = indec.leer_capitulo_anual(ruta)
            for anio, valor in cuadro["capitulo27"].items():
                cap27[flujo][anio] = valor
                archivo[(flujo, anio)] = nombre
            for anio, total in cuadro["total"].items():
                cociente = total / anual.loc[anio, f"{flujo}_total_musd"]
                unidades.append({"archivo": nombre, "anio": anio, "total_cuadro": total,
                                 "total_oficial": anual.loc[anio, f"{flujo}_total_musd"], "cociente": cociente,
                                 "estado": "OK" if 0.8 <= cociente <= 1.25 else "REVISAR"})
    unidades = pd.DataFrame(unidades)
    anual["expo_cap27_musd"] = pd.Series(cap27["expo"])
    anual["impo_cap27_musd"] = pd.Series(cap27["impo"])
    anual["fuente_cap27"] = [f"INDEC, {archivo[('expo', a)]} y {archivo[('impo', a)]}"
                             if ("expo", a) in archivo else None for a in anual.index]
    # Años sin cuadro anual por capítulo (antes de 2010): suma de los 12 meses de la API (antes de
    # 2018 la base no tenía secreto estadístico, así que el total es completo).
    for anio in range(int(DESDE[:4]), min(cap27["expo"])):
        meses = cap27_mensual.loc[str(anio)]
        if len(meses) != 12 or (meses["fuente"] != FUENTE_API).any():
            raise ValueError(f"{anio}: se esperaban 12 meses de la API")
        anual.loc[anio, ["expo_cap27_musd", "impo_cap27_musd"]] = meses[["expo_cap27_musd", "impo_cap27_musd"]].sum().values
        anual.loc[anio, "fuente_cap27"] = "Suma de los 12 meses de la API (no hay cuadro anual por capítulo)"
    anual["saldo_cap27_musd"] = anual["expo_cap27_musd"] - anual["impo_cap27_musd"]
    anual["archivo_expo_rubros"] = nombres["expo_anual_rubros"]
    anual["archivo_impo_usos"] = nombres["impo_anual_usos"]
    anual.index.name = "anio"
    columnas = ["expo_total_musd", "impo_total_musd", "expo_cye_musd", "impo_cyl_musd", "saldo_total_musd", "provisorio",
                "expo_cap27_musd", "impo_cap27_musd", "fuente_cap27", "saldo_cap27_musd", "archivo_expo_rubros", "archivo_impo_usos"]
    return anual[columnas], unidades


def acumulados_revisados(cuadros: list[dict]) -> dict:
    """Capítulo 27: acumulado oficial más reciente de enero hasta cada mes, para cada año. Cada
    informe da el acumulado hasta m y, restando el mes m, el acumulado hasta m - 1 (misma revisión).
    Para cada año y mes queda el del informe publicado más recientemente."""
    acumulados = {}

    def proponer(anio, mes, fecha, valores, origen):
        vigente = acumulados.get((anio, mes))
        if vigente is None or fecha > vigente["fecha"]:
            acumulados[(anio, mes)] = {"fecha": fecha, "valores": valores, "origen": origen}

    for cuadro in cuadros:
        c27, fecha = cuadro["cap27"], cuadro["fecha_publicacion"]
        m = c27["mes"].month
        for anio, clave_acumulado, clave_mes in ((c27["mes"].year, "actual", "mes_actual"),
                                                 (c27["mes"].year - 1, "anterior", "mes_anterior")):
            acumulado, valor_mes = c27["acumulado"][clave_acumulado], c27[clave_mes]
            proponer(anio, m, fecha, acumulado, f"ene-{m:02d}/{anio} del informe {fecha:%d/%m/%Y}")
            if m > 1:
                proponer(anio, m - 1, fecha, {k: acumulado[k] - valor_mes[k] for k in acumulado},
                         f"ene-{m - 1:02d}/{anio} (acum. ene-{m:02d} menos mes {m:02d}) del informe {fecha:%d/%m/%Y}")
    return acumulados


def armar_cap27_mensual(api: pd.DataFrame, cuadros: list[dict]) -> pd.DataFrame:
    """Capítulo 27 mensual (control): mes(m) = acum(m) - acum(m-1), con acum(0) = 0, de los acumulados
    oficiales más recientes; los meses anteriores a la ventana de informes salen de la API."""
    acumulados = acumulados_revisados(cuadros)
    derivados = {}
    for (anio, mes), info in sorted(acumulados.items()):
        if mes == 1:
            previo, origen_previo = {k: 0.0 for k in info["valores"]}, None
        elif (anio, mes - 1) in acumulados:
            previo, origen_previo = acumulados[(anio, mes - 1)]["valores"], acumulados[(anio, mes - 1)]["origen"]
        else:
            continue
        fuente = f"INDEC: acum. {info['origen']}" + (f" - acum. {origen_previo}" if origen_previo else "")
        derivados[pd.Timestamp(anio, mes, 1)] = {
            "expo_cap27_musd": info["valores"]["expo"] - previo["expo"], "impo_cap27_musd": info["valores"]["impo"] - previo["impo"],
            "saldo_cap27_musd": info["valores"]["saldo"] - previo["saldo"], "fuente": fuente}
    desde_informes = pd.DataFrame.from_dict(derivados, orient="index")
    desde_api = api[~api.index.isin(desde_informes.index)].copy()
    desde_api["saldo_cap27_musd"] = desde_api["expo_cap27_musd"] - desde_api["impo_cap27_musd"]
    desde_api["fuente"] = FUENTE_API
    mensual = pd.concat([desde_api, desde_informes]).sort_index()
    mensual.index.name = "fecha"
    return mensual[["expo_cap27_musd", "impo_cap27_musd", "saldo_cap27_musd", "fuente"]]


def armar_acumulados(cuadros: list[dict]) -> pd.DataFrame:
    """Acumulados oficiales (enero al mes del informe) que publica cada informe, del año en curso
    (acum_) y del anterior (acum_ant_). Índice: fecha de publicación del informe."""
    filas = {}
    for cuadro in sorted(cuadros, key=lambda c: c["fecha_publicacion"]):
        ru, c1, c27 = cuadro["rubros_usos"], cuadro["cuadro1"], cuadro["cap27"]
        fila = {"mes_informe": ru["mes"].strftime("%Y-%m-%d"), "archivo": cuadro["archivo"],
                "hoja_expo": ru["hojas"]["expo"], "hoja_impo": ru["hojas"]["impo"]}
        for prefijo, clave in (("acum", "actual"), ("acum_ant", "anterior")):
            fila[f"{prefijo}_expo_total_musd"] = c1[clave]["expo"]
            fila[f"{prefijo}_impo_total_musd"] = c1[clave]["impo"]
            fila[f"{prefijo}_saldo_total_musd"] = c1[clave]["saldo"]
            fila[f"{prefijo}_expo_cye_musd"] = ru["acumulado"][clave]["expo_cye"]
            fila[f"{prefijo}_impo_cyl_musd"] = ru["acumulado"][clave]["impo_cyl"]
            for flujo in ("expo", "impo", "saldo"):
                fila[f"{prefijo}_{flujo}_cap27_musd"] = c27["acumulado"][clave][flujo] if c27 else None
        filas[cuadro["fecha_publicacion"]] = fila
    tabla = pd.DataFrame.from_dict(filas, orient="index")
    tabla.index.name = "fecha_publicacion"
    return tabla


# ---------------------------------------------------------------------------------------------
# 3. Controles y validación
# ---------------------------------------------------------------------------------------------
def etiqueta_acumulado(mes: pd.Timestamp, anio: int) -> str:
    return f"{anio} ene-{indec.MESES_ABREV[mes.month - 1].lower()}"


def controles_generales(cap27, ica, anual, cuadros, ultimo) -> list[dict]:
    resultados = []

    def anotar(control, ok, detalle):
        resultados.append({"control": control, "estado": "OK" if ok else "REVISAR", "detalle": detalle})

    for nombre, tabla in (("rubros y usos", ica), ("capítulo 27 (control)", cap27)):
        faltan = pd.date_range(tabla.index.min(), tabla.index.max(), freq="MS").difference(tabla.index)
        anotar(f"Serie mensual {nombre} sin meses faltantes", len(faltan) == 0,
               f"{tabla.index.min():%m/%Y} a {tabla.index.max():%m/%Y}; faltan: {list(faltan.strftime('%m/%Y'))}")
    mes = ultimo["rubros_usos"]["mes"]
    anotar("Serie mensual rubros y usos: de enero de 2004 al mes del último informe",
           ica.index.min() == pd.Timestamp(DESDE) and ica.index.max() == mes, f"{ica.index.min():%m/%Y} a {ica.index.max():%m/%Y}")
    ok = ((ica["expo_cye_musd"] >= 0) & (ica["expo_cye_musd"] <= ica["expo_total_musd"])
          & (ica["impo_cyl_musd"] >= 0) & (ica["impo_cyl_musd"] <= ica["impo_total_musd"])).all()
    anotar("0 <= CyE <= exportaciones totales y 0 <= CyL <= importaciones totales, todos los meses", ok, "")
    completos = ica.groupby(ica.index.year).filter(lambda x: len(x) == 12)
    suma = completos.groupby(completos.index.year)[["expo_total_musd", "impo_total_musd", "expo_cye_musd", "impo_cyl_musd"]].sum()
    comunes = suma.index.intersection(anual.index)
    dif = (suma.loc[comunes] - anual.loc[comunes, suma.columns]).abs().max().max()
    anotar("Rubros y usos mensual = anuales oficiales (totales, CyE, CyL)", dif < 0.01,
           f"{comunes.min()}-{comunes.max()}; diferencia máxima {dif:.6f} MUSD")
    for clave, anio in (("actual", mes.year), ("anterior", mes.year - 1)):
        meses = ica.loc[f"{anio}-01-01":f"{anio}-{mes.month:02d}-01"]
        acum_ru = ultimo["rubros_usos"]["acumulado"][clave]
        dif = max(abs(meses["expo_total_musd"].sum() - ultimo["cuadro1"][clave]["expo"]),
                  abs(meses["impo_total_musd"].sum() - ultimo["cuadro1"][clave]["impo"]))
        anotar(f"Rubros y usos ene-{mes.month:02d}/{anio}: totales = acumulado del cuadro 1", dif < 0.01, f"diferencia máxima {dif:.6f} MUSD")
        dif = max(abs(meses["expo_cye_musd"].sum() - acum_ru["expo_cye"]), abs(meses["impo_cyl_musd"].sum() - acum_ru["impo_cyl"]))
        anotar(f"Rubros y usos ene-{mes.month:02d}/{anio}: CyE y CyL = acumulados de las hojas "
               f"{ultimo['rubros_usos']['hojas']['expo']} y {ultimo['rubros_usos']['hojas']['impo']}", dif < 0.01,
               f"diferencia máxima {dif:.6f} MUSD")
        dif = max(abs(acum_ru["expo_total"] - ultimo["cuadro1"][clave]["expo"]), abs(acum_ru["impo_total"] - ultimo["cuadro1"][clave]["impo"]))
        anotar(f"Último informe, {anio}: totales de las hojas de rubros y usos = cuadro 1", dif < 0.01, f"diferencia máxima {dif:.6f} MUSD")
    dif = max(abs(c["cap27"][p]["expo"] - c["cap27"][p]["impo"] - c["cap27"][p]["saldo"]) for c in cuadros for p in ("mes_actual", "mes_anterior"))
    anotar("Capítulo 27 (control): saldo = expo - impo en los cuadros", dif < 0.01, f"diferencia máxima {dif:.6f} MUSD")
    ok = ((cap27["expo_cap27_musd"] <= ica["expo_total_musd"].reindex(cap27.index).fillna(float("inf")))
          & (cap27["impo_cap27_musd"] <= ica["impo_total_musd"].reindex(cap27.index).fillna(float("inf")))
          & (cap27[["expo_cap27_musd", "impo_cap27_musd"]] >= 0).all(axis=1)).all()
    anotar("Capítulo 27 (control): 0 <= capítulo 27 <= total, todos los meses", ok, "exportaciones e importaciones")
    return resultados


def control_publicados(cuadros: list[dict]) -> pd.DataFrame:
    """Lo leído de los Excel de cuadros vs. lo publicado en los informes (PDF)."""
    por_fecha = {c["fecha_publicacion"]: c for c in cuadros}
    filas = []
    for dato, fecha, cuadro, claves, publicado, donde in CONTROLES_PUBLICADOS:
        informe = por_fecha.get(pd.Timestamp(fecha))
        if informe is None:
            filas.append({"dato": dato, "estado": "SIN INFORME", "donde": donde})
            continue
        valor = informe[cuadro]
        for clave in claves:
            valor = valor[clave]
        filas.append({"dato": dato, "valor_leido": round(valor, 2), "valor_publicado": publicado, "diferencia": round(valor - publicado, 2),
                      "estado": "OK" if abs(valor - publicado) <= TOLERANCIA_MUSD else "REVISAR", "donde": donde})
    return pd.DataFrame(filas)


def meses_publicados(cuadros: list[dict]) -> pd.DataFrame:
    """Capítulo 27: cada mes tal como lo publica el informe más reciente que lo trae (sin derivar)."""
    publicados = {}
    for cuadro in sorted(cuadros, key=lambda c: c["fecha_publicacion"]):
        c27, fecha = cuadro["cap27"], cuadro["fecha_publicacion"]
        publicados[c27["mes"] - pd.DateOffset(years=1)] = {**c27["mes_anterior"], "informe": f"{fecha:%d/%m/%Y}"}
        publicados[c27["mes"]] = {**c27["mes_actual"], "informe": f"{fecha:%d/%m/%Y}"}
    tabla = pd.DataFrame.from_dict(publicados, orient="index").sort_index()
    tabla.index.name = "fecha"
    return tabla


def cap27_anual_vs_informes(anual: pd.DataFrame, de_enero: list[dict], anios: list[int]) -> pd.DataFrame:
    """Capítulo 27 anual oficial vs. los informes de diciembre (primera publicación y revisión un año
    después). Las diferencias son vigente menos informe."""
    por_anio = {c["fecha_publicacion"].year: c for c in de_enero}
    filas = []
    for anio in anios:
        for version, anio_publicacion, clave in (("primera publicación", anio + 1, "actual"), ("revisada un año después", anio + 2, "anterior")):
            base = {"anio": anio, "version": version}
            cuadro = por_anio.get(anio_publicacion)
            if cuadro is None:
                filas.append({**base, "estado": "TODAVIA NO PUBLICADO"})
                continue
            base["informe"] = f"{cuadro['fecha_publicacion']:%d/%m/%Y}"
            if cuadro["cap27"] is None:
                filas.append({**base, "estado": "EL INFORME NO TRAE EL CUADRO DEL CAPITULO 27"})
                continue
            fila = dict(base)
            for c in ("expo", "impo", "saldo"):
                fila[f"{c}_informe"] = cuadro["cap27"]["acumulado"][clave][c]
                fila[f"{c}_anual_oficial"] = anual.loc[anio, f"{c}_cap27_musd"]
                fila[f"dif_{c}"] = anual.loc[anio, f"{c}_cap27_musd"] - cuadro["cap27"]["acumulado"][clave][c]
            fila["anual_oficial_de"] = anual.loc[anio, "fuente_cap27"]
            fila["estado"] = "OK" if abs(fila["dif_saldo"]) <= TOLERANCIA_MUSD else "REVISION POSTERIOR DEL INDEC"
            filas.append(fila)
    return pd.DataFrame(filas)


def cap27_suma_de_meses(cap27: pd.DataFrame, anual: pd.DataFrame, cuadros: list[dict]) -> pd.DataFrame:
    """Capítulo 27: suma de los meses vs. anuales y acumulados oficiales (con el último informe tiene
    que dar cero; con los anteriores muestra cuánto revisó después el INDEC)."""
    columnas = ["expo_cap27_musd", "impo_cap27_musd", "saldo_cap27_musd"]
    filas, meses_por_anio = [], cap27.groupby(cap27.index.year).size()
    for anio in anual.index:
        if anio < int(DESDE[:4]) or meses_por_anio.get(anio, 0) != 12 or pd.isna(anual.loc[anio, "saldo_cap27_musd"]):
            continue
        suma = cap27.loc[str(anio), columnas].sum()
        filas.append({"periodo": str(anio), "oficial": "anual", "fuente_oficial": anual.loc[anio, "fuente_cap27"],
                      **{f"{c}_suma_meses": suma[c] for c in columnas}, **{f"{c}_oficial": anual.loc[anio, c] for c in columnas}})
    for cuadro in cuadros:
        c27 = cuadro["cap27"]
        mes = c27["mes"]
        for anio, clave in ((mes.year, "actual"), (mes.year - 1, "anterior")):
            suma = cap27.loc[f"{anio}-01-01":f"{anio}-{mes.month:02d}-01", columnas].sum()
            oficial = c27["acumulado"][clave]
            filas.append({"periodo": etiqueta_acumulado(mes, anio), "oficial": "acumulado",
                          "fuente_oficial": f"Informe ICA del {cuadro['fecha_publicacion']:%d/%m/%Y}",
                          **{f"{c}_suma_meses": suma[c] for c in columnas},
                          "expo_cap27_musd_oficial": oficial["expo"], "impo_cap27_musd_oficial": oficial["impo"],
                          "saldo_cap27_musd_oficial": oficial["saldo"]})
    tabla = pd.DataFrame(filas)
    for c in columnas:
        tabla[f"{c}_dif"] = tabla[f"{c}_suma_meses"] - tabla[f"{c}_oficial"]
    return tabla


def cap27_api_vs_informes(api: pd.DataFrame, cap27: pd.DataFrame) -> pd.DataFrame:
    comunes = api.index.intersection(cap27[cap27["fuente"] != FUENTE_API].index)
    tabla = pd.DataFrame({"expo_api": api.loc[comunes, "expo_cap27_musd"], "expo_informe": cap27.loc[comunes, "expo_cap27_musd"],
                          "impo_api": api.loc[comunes, "impo_cap27_musd"], "impo_informe": cap27.loc[comunes, "impo_cap27_musd"],
                          "fuente_informe": cap27.loc[comunes, "fuente"]})
    tabla["dif_expo"] = tabla["expo_api"] - tabla["expo_informe"]
    tabla["dif_impo"] = tabla["impo_api"] - tabla["impo_informe"]
    tabla.index.name = "fecha"
    return tabla


def cap27_publicado_vs_derivado(cap27: pd.DataFrame, cuadros: list[dict]) -> pd.DataFrame:
    publicados = meses_publicados(cuadros)
    comunes = publicados.index.intersection(cap27.index)
    tabla = pd.DataFrame({"saldo_publicado": publicados.loc[comunes, "saldo"], "informe_publicado": publicados.loc[comunes, "informe"],
                          "saldo_derivado": cap27.loc[comunes, "saldo_cap27_musd"]})
    tabla["dif_saldo"] = tabla["saldo_derivado"] - tabla["saldo_publicado"]
    tabla.index.name = "fecha"
    return tabla


def cap27_comex_vs_oficial(anual: pd.DataFrame, ultimo: dict, registros: list) -> pd.DataFrame:
    """Capítulo 27 en la base comex (microdatos por posición NCM) vs. lo oficial: documenta por qué esa
    base no es la fuente principal (desde 2018 el secreto estadístico tapa parte de las exportaciones)."""
    mes = ultimo["cap27"]["mes"]
    filas = []
    for anio in ANIOS_COMEX + [mes.year]:
        sumas = {}
        for flujo, clave in (("exports", "expo"), ("imports", "impo")):
            ruta, registro = indec_comex.descargar_base(flujo, anio)
            registros.append(registro)
            base = indec_comex.leer_base(ruta)
            del_capitulo = base[base["ncm"].str.startswith("27")]
            sumas[clave] = del_capitulo.groupby("mes")["valor_usd"].sum() / 1e6  # USD -> millones de USD
        if anio == mes.year:
            periodo = etiqueta_acumulado(mes, anio)
            acum = ultimo["cap27"]["acumulado"]["actual"]
            oficial = {"expo_cap27_musd": acum["expo"], "impo_cap27_musd": acum["impo"]}
            fuente = f"Acumulado oficial del último informe (ICA del {ultimo['fecha_publicacion']:%d/%m/%Y})"
            meses = int(sumas["expo"].index.max())
        else:
            periodo, oficial, fuente, meses = str(anio), anual.loc[anio], anual.loc[anio, "fuente_cap27"], 12
        fila = {"periodo": periodo, "meses_en_base": meses,
                "expo_comex_musd": sumas["expo"].sum(), "expo_oficial_musd": oficial["expo_cap27_musd"],
                "impo_comex_musd": sumas["impo"].sum(), "impo_oficial_musd": oficial["impo_cap27_musd"], "referencia_oficial": fuente}
        fila["dif_expo_musd"] = fila["expo_comex_musd"] - fila["expo_oficial_musd"]
        fila["dif_expo_pct"] = 100 * fila["dif_expo_musd"] / fila["expo_oficial_musd"]
        fila["dif_impo_musd"] = fila["impo_comex_musd"] - fila["impo_oficial_musd"]
        filas.append(fila)
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------------------------
# armar()
# ---------------------------------------------------------------------------------------------
def armar() -> dict:
    datos = leer()
    cuadros, ultimo = datos["cuadros"], datos["ultimo"]
    ultimo_mes = ultimo["rubros_usos"]["mes"]
    ica = armar_ica_mensual(datos["rubros_usos_largo"], ultimo_mes)
    cap27 = armar_cap27_mensual(datos["api"], cuadros)
    anual, unidades = armar_anual(datos["rutas"], datos["nombres"], datos["capitulos"], cap27)
    acumulados = armar_acumulados(sorted({c["fecha_publicacion"]: c for c in cuadros + datos["de_enero"]}.values(),
                                         key=lambda c: c["fecha_publicacion"]))

    publicados = control_publicados(cuadros)
    suma_meses_27 = cap27_suma_de_meses(cap27, anual, cuadros)
    anuales_27 = cap27_anual_vs_informes(anual, datos["de_enero"], list(range(PRIMER_ANIO_CONTRASTE, ultimo_mes.year)))
    comex = cap27_comex_vs_oficial(anual, ultimo, datos["registros"])

    controles = controles_generales(cap27, ica, anual, cuadros, ultimo)
    ultimo_27 = suma_meses_27[suma_meses_27["fuente_oficial"] == f"Informe ICA del {ultimo['fecha_publicacion']:%d/%m/%Y}"]
    dif_27 = ultimo_27["saldo_cap27_musd_dif"].abs().max()
    controles += [
        {"control": "Valores leídos de los Excel de cuadros = publicados en el PDF de los informes",
         "estado": "OK" if (publicados["estado"].isin(["OK", "SIN INFORME"])).all() else "REVISAR",
         "detalle": f"{int((publicados['estado'] == 'OK').sum())} OK, {int((publicados['estado'] == 'SIN INFORME').sum())} sin informe en la ventana"},
        {"control": "Capítulo 27 (control): unidades de los cuadros por capítulo (total del cuadro / total oficial)",
         "estado": "OK" if (unidades["estado"] == "OK").all() else "REVISAR",
         "detalle": f"cociente entre {unidades['cociente'].min():.4f} y {unidades['cociente'].max():.4f}"},
        {"control": "Capítulo 27 (control): suma de los meses = acumulados oficiales del último informe",
         "estado": "OK" if dif_27 < 0.01 else "REVISAR", "detalle": f"diferencia máxima {dif_27:.6f} MUSD"},
        {"control": "Capítulo 27 en la base comex vs. oficial (secreto estadístico desde 2018)", "estado": "EVIDENCIA",
         "detalle": "; ".join(f"{f.periodo}: exportaciones {f.dif_expo_pct:+.1f}%" for f in comex.itertuples())},
    ]
    registros = pd.DataFrame(datos["registros"]).drop(columns=["descargado"], errors="ignore")
    return {
        "series": {"ica_mensual.csv": ica, "ica_anual.csv": anual, "ica_cap27_mensual.csv": cap27,
                   "ica_acumulados_informes.csv": acumulados},
        "controles": pd.DataFrame(controles),
        "validacion": {
            "control_valores_publicados.csv": (publicados, {"index": False}),
            "control_unidades_cuadros_capitulos.csv": (unidades, {"index": False, "float_format": "%.4f"}),
            "cap27_suma_meses_vs_oficial.csv": (suma_meses_27, {"index": False, "float_format": "%.2f"}),
            "cap27_api_vs_informes.csv": (cap27_api_vs_informes(datos["api"], cap27), {"float_format": "%.2f"}),
            "cap27_mes_publicado_vs_derivado.csv": (cap27_publicado_vs_derivado(cap27, cuadros), {"float_format": "%.2f"}),
            "cap27_anual_vs_informes.csv": (anuales_27, {"index": False, "float_format": "%.2f"}),
            "cap27_comex_vs_oficial.csv": (comex, {"index": False, "float_format": "%.1f"}),
            "informes_ica_usados.csv": (datos["informes"], {"index": False}),
            "metadatos_series_api.csv": (datos["metadatos"], {"index": False}),
            "descargas.csv": (registros, {"index": False}),
        },
        "registros": datos["registros"],
    }
