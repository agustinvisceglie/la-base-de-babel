"""
Nota "La vuelta del gas" (El Pozo y el Péndulo, diciembre 2026). Etapa 1: saldo energético.

Pregunta de la nota: ¿cuánto del saldo comercial de bienes de la Argentina explica hoy la energía,
y cuánto de eso es estructural (más producción) y cuánto coyuntural (precios internacionales)?

Definición de energía: capítulo 27 de la Nomenclatura Común del Mercosur (NCM), "Combustibles
minerales, aceites minerales y productos de su destilación; materias bituminosas; ceras minerales",
la misma de los dos lados (exportaciones e importaciones), como en la sección 3.4 del informe
técnico del Intercambio comercial argentino (ICA) del INDEC.

Qué hace este script:
    1. Arma la serie mensual del capítulo 27 (exportaciones, importaciones y saldo):
       - De cada informe técnico del ICA publicado desde que la API de Series de Tiempo dejó de
         actualizarse toma el cuadro del capítulo 27 (año en curso y anterior). Con cada informe
         arma acumulados oficiales: el acumulado hasta m y, restándole el mes m, el acumulado
         revisado hasta m - 1. Para cada año y mes queda el acumulado del informe más reciente,
         y cada mes es la diferencia entre acumulados consecutivos. Así la suma de los meses
         coincide con el acumulado oficial más reciente. Cuando sale un informe nuevo, sus
         acumulados reemplazan solos a los viejos.
       - Los meses que ningún informe cubre salen de la API de Series de Tiempo.
    2. Arma la serie mensual del intercambio comercial (totales, CyE y CyL) con la serie oficial
       por rubros y usos que publica la versión interactiva del informe más reciente.
    3. Arma la tabla anual oficial: totales, CyE y CyL (cuadros anuales por rubro y uso) y
       capítulo 27 (cuadros anuales por capítulo; para cada año, el cuadro más reciente).
    4. Genera g1 y g2 (CSV para Datawrapper y PNG de control) y las cifras para citar en el
       texto, que salen solo de anuales y acumulados oficiales, nunca de sumar meses.
    5. Corre los controles y la comparación con la definición CyE - CyL.

Fuentes (todas del INDEC; detalle y URL en informe_validacion.md):
    - Informes técnicos del ICA: listado oficial (www.indec.gob.ar/Institucional/Indec/InformesTecnicos/40),
      Excel de cuadros de cada informe (ica_cuadros_DD_MM_AA.xls) y serie_rubros_usos_mensual.xlsx
      de la versión interactiva del informe más reciente.
    - Cuadros anuales: exp_gr_80_AA.xls e imp_uso_econ_80_AA.xls (rubros y usos), exp_ncm_AA_AA.xls
      e imp_ncm_AA_AA.xls (capítulos de la NCM, quinquenios desde 2010-2014).
    - API de Series de Tiempo (publica la Subsecretaría de Programación Macroeconómica, fuente
      INDEC): 162.3_XMB_MINION_0_0_56 y 163.3_MMBUSTIION_0_0_59 (capítulo 27, mensual, hasta 02/2025).

Genera:
    - datos/procesados/ica_cap27_mensual.csv   capítulo 27 mensual desde 2005, con la fuente de cada mes
    - datos/procesados/ica_mensual.csv         totales, CyE y CyL mensual desde 2004
    - datos/procesados/ica_anual.csv           anual oficial: totales, CyE, CyL y capítulo 27
    - cifras_para_el_texto.csv                 cifras citables (solo anuales y acumulados oficiales)
    - graficos/g1_balanza_energetica_anual.csv y .png
    - graficos/g2_saldo_energetico_vs_total_12m.csv y .png
    - validacion/*.csv                         controles, comparaciones, informes usados y descargas

Uso (desde la raíz del repositorio):
    .venv/Scripts/python notas/2026-12-la-vuelta-del-gas/1_ica.py
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))  # para poder importar scripts/ al correr este archivo directamente

import matplotlib

matplotlib.use("Agg")  # sin ventanas: solo guarda los PNG
import matplotlib.pyplot as plt
import pandas as pd

from scripts import api_series_tiempo, indec
from scripts.descargas import PROCESADOS, guardar_registro

CARPETA_NOTA = Path(__file__).resolve().parent
GRAFICOS = CARPETA_NOTA / "graficos"
VALIDACION = CARPETA_NOTA / "validacion"

# Se baja desde 2005 solo para que el acumulado de 12 meses (g2) arranque en enero de 2006.
DESDE = "2005-01-01"
PRIMER_ANIO_NOTA = 2006

# API de Series de Tiempo: capítulo 27, mensual, millones de USD (exportaciones FOB, importaciones CIF).
SERIES_API_CAP27 = {
    "162.3_XMB_MINION_0_0_56": "expo_cap27_musd",
    "163.3_MMBUSTIION_0_0_59": "impo_cap27_musd",
}

# Cuadros que se buscan en la página del ICA por el comienzo del nombre (cambia cada año).
ARCHIVOS_PAGINA_ICA = {
    "expo_anual_rubros": "exp_gr_80_",
    "impo_anual_usos": "imp_uso_econ_80_",
    "expo_anual_capitulos": "exp_ncm_",
    "impo_anual_capitulos": "imp_ncm_",
}
# Cuadros anuales por capítulo de quinquenios anteriores (siguen en el servidor del INDEC pero
# ya no se enlazan en la página). Ordenados del más viejo al más nuevo.
QUINQUENIOS_CAPITULOS = ["10_14", "12_16", "13_17", "14_18", "15_19", "16_20", "17_21", "18_22", "19_23", "20_24"]

# Valores publicados por el INDEC para contrastar con lo que leemos de los Excel de cuadros.
# (dato, fecha de publicación del informe, cuadro, dato dentro del cuadro, valor publicado, dónde)
CONTROLES_PUBLICADOS = [
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
    ("Exportaciones totales, acum. ene-sep 2026", "2026-10-19", "cuadro1", ("actual", "expo"), 77267,
     "Informe ICA de septiembre 2026 (19/10/2026), p. 7, cuadro 1"),
    ("Importaciones totales, acum. ene-sep 2026", "2026-10-19", "cuadro1", ("actual", "impo"), 56069, "Ídem"),
    ("Saldo comercial de bienes, acum. ene-sep 2026", "2026-10-19", "cuadro1", ("actual", "saldo"), 21198, "Ídem"),
    ("Saldo comercial de bienes, acum. ene-sep 2025", "2026-10-19", "cuadro1", ("anterior", "saldo"), 6046, "Ídem"),
]
TOLERANCIA_MUSD = 1.0  # los informes redondean a millones enteros

FUENTE_API = "API Series de Tiempo (INDEC; publica SSPM)"


# ---------------------------------------------------------------------------------------------
# 1. Descargas y lectura
# ---------------------------------------------------------------------------------------------
def bajar_datos() -> dict:
    """Baja todo lo necesario. Devuelve un diccionario con las tablas leídas y los registros."""
    registros = []

    print("API de Series de Tiempo (capítulo 27)...")
    api, regs = api_series_tiempo.descargar_series(list(SERIES_API_CAP27), "cap27_mensual", DESDE)
    registros += regs
    metadatos, regs = api_series_tiempo.descargar_metadatos(list(SERIES_API_CAP27), "cap27_mensual")
    registros += regs
    api = api.rename(columns=SERIES_API_CAP27).dropna()

    print("Cuadros anuales del INDEC...")
    urls, regs = indec.buscar_archivos(indec.PAGINA_ICA, list(ARCHIVOS_PAGINA_ICA.values()), "pagina_ica.html")
    registros += regs
    rutas = {}
    for clave, prefijo in ARCHIVOS_PAGINA_ICA.items():
        rutas[clave], registro = indec.descargar_archivo(urls[prefijo])
        registros.append(registro)
    capitulos = {"expo": [], "impo": []}  # del cuadro más viejo al más nuevo
    for quinquenio in QUINQUENIOS_CAPITULOS:
        for flujo, prefijo in (("expo", "exp"), ("impo", "imp")):
            ruta, registro = indec.descargar_archivo(f"{indec.URL_INDEC}/ftp/cuadros/economia/{prefijo}_ncm_{quinquenio}.xls")
            capitulos[flujo].append(ruta)
            registros.append(registro)
    capitulos["expo"].append(rutas["expo_anual_capitulos"])
    capitulos["impo"].append(rutas["impo_anual_capitulos"])

    print("Informes técnicos del ICA...")
    informes_todos, regs = indec.listar_informes_ica("listado_informes_ica.html")
    registros += regs
    # Se usan todos los informes publicados desde el mes siguiente al último dato de la API.
    primer_informe = api.index.max() + pd.DateOffset(months=1)
    informes = informes_todos[informes_todos["fecha_publicacion"] >= primer_informe].reset_index(drop=True)
    cuadros = []
    for informe in informes.itertuples():
        ruta, registro = indec.descargar_archivo(informe.url_cuadros)
        registros.append(registro)
        cuadros.append({"fecha_publicacion": informe.fecha_publicacion,
                        "cap27": indec.leer_cuadro_capitulo27(ruta),
                        "cuadro1": indec.leer_cuadro1_acumulado(ruta)})
    print(f"    {len(cuadros)} informes, del {informes.fecha_publicacion.min():%d/%m/%Y} "
          f"al {informes.fecha_publicacion.max():%d/%m/%Y}")

    print("Serie mensual por rubros y usos (versión interactiva del último informe)...")
    ultimo = informes.iloc[-1]
    ruta_rubros, registro = indec.descargar_archivo(ultimo.url_interactivo + "data/cuadros/serie_rubros_usos_mensual.xlsx")
    registros.append(registro)

    informes["mes_del_informe"] = [c["cap27"]["mes"].strftime("%Y-%m") for c in cuadros]
    return {
        "api": api, "metadatos": metadatos, "rutas": rutas, "capitulos": capitulos,
        "informes": informes, "informes_todos": informes_todos, "cuadros": cuadros,
        "rubros_usos": indec.leer_rubros_usos_mensual(ruta_rubros), "registros": registros,
    }


# ---------------------------------------------------------------------------------------------
# 2. Series
# ---------------------------------------------------------------------------------------------
def acumulados_revisados(cuadros: list[dict]) -> dict:
    """Acumulado oficial más reciente de enero hasta cada mes, para cada año.

    Cada informe publica, con una misma revisión, el acumulado de enero al mes m y el valor del
    mes m, para el año en curso y para el anterior. De ahí salen dos acumulados oficiales:
        acumulado hasta m      = el acumulado del informe
        acumulado hasta m - 1  = el acumulado del informe - el mes m del informe
    (por ejemplo, el informe de febrero da ene-feb y, restando febrero, enero revisado).
    Para cada año y mes queda el acumulado del informe publicado más recientemente.
    Devuelve {(año, mes): {"fecha", "valores": {"expo", "impo", "saldo"}, "origen"}}.
    """
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
    """Capítulo 27 mensual a partir de los acumulados oficiales más recientes.

    Cada mes es la diferencia entre acumulados consecutivos: mes(m) = acum(m) - acum(m-1), con
    acum(0) = 0. Así, la suma de los meses de enero a m es exactamente el acumulado oficial más
    reciente hasta m. Es aritmética sobre cifras publicadas, no una estimación. Cuando sale un
    informe nuevo, sus acumulados reemplazan solos a los más viejos.
    Los meses sin acumulados publicados (antes de la ventana de informes) salen de la API.
    """
    acumulados = acumulados_revisados(cuadros)
    derivados = {}
    for (anio, mes), info in sorted(acumulados.items()):
        if mes == 1:
            previo, origen_previo = {k: 0.0 for k in info["valores"]}, None
        elif (anio, mes - 1) in acumulados:
            previo = acumulados[(anio, mes - 1)]["valores"]
            origen_previo = acumulados[(anio, mes - 1)]["origen"]
        else:
            continue  # sin acumulado del mes anterior no se puede derivar el mes
        fuente = f"INDEC: acum. {info['origen']}" + (f" - acum. {origen_previo}" if origen_previo else "")
        derivados[pd.Timestamp(anio, mes, 1)] = {
            "expo_cap27_musd": info["valores"]["expo"] - previo["expo"],
            "impo_cap27_musd": info["valores"]["impo"] - previo["impo"],
            "saldo_cap27_musd": info["valores"]["saldo"] - previo["saldo"],
            "fuente": fuente,
        }
    desde_informes = pd.DataFrame.from_dict(derivados, orient="index")

    desde_api = api[~api.index.isin(desde_informes.index)].copy()
    desde_api["saldo_cap27_musd"] = desde_api["expo_cap27_musd"] - desde_api["impo_cap27_musd"]
    desde_api["fuente"] = FUENTE_API

    mensual = pd.concat([desde_api, desde_informes]).sort_index()
    mensual.index.name = "fecha"
    return mensual[["expo_cap27_musd", "impo_cap27_musd", "saldo_cap27_musd", "fuente"]]


def meses_publicados(cuadros: list[dict]) -> pd.DataFrame:
    """Valor mensual tal como lo publica el informe más reciente que trae ese mes (sin derivar).
    Solo se usa para comparar con los meses derivados de los acumulados."""
    publicados = {}
    for cuadro in sorted(cuadros, key=lambda c: c["fecha_publicacion"]):
        c27, fecha = cuadro["cap27"], cuadro["fecha_publicacion"]
        publicados[c27["mes"] - pd.DateOffset(years=1)] = {**c27["mes_anterior"], "informe": f"{fecha:%d/%m/%Y}"}
        publicados[c27["mes"]] = {**c27["mes_actual"], "informe": f"{fecha:%d/%m/%Y}"}
    tabla = pd.DataFrame.from_dict(publicados, orient="index").sort_index()
    tabla.index.name = "fecha"
    return tabla


def armar_ica_mensual(rubros_usos: pd.DataFrame) -> pd.DataFrame:
    """Totales, CyE y CyL mensuales (serie oficial por rubros y usos)."""
    ica = rubros_usos.copy()
    ica["saldo_total_musd"] = ica["expo_total_musd"] - ica["impo_total_musd"]
    ica["saldo_cye_cyl_musd"] = ica["expo_cye_musd"] - ica["impo_cyl_musd"]
    return ica


def armar_anual(rutas: dict, capitulos: dict, cap27_mensual: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Tabla anual oficial: totales, CyE, CyL y capítulo 27 (revisión más reciente de cada año).

    Devuelve también el control de unidades de los cuadros por capítulo: el "Total" de cada
    cuadro tiene que parecerse al total anual oficial (cociente entre 0,97 y 1,03). Si un cuadro
    viniera en miles en vez de millones, el cociente daría 1.000 y el control fallaría; las
    diferencias chicas son revisiones posteriores del INDEC (la mayor, 5%, es el 2014 estimado
    del cuadro 2010-2014, que el INDEC revisó en 2016; ese valor no se usa porque hay cuadros más nuevos).
    """
    expo = indec.leer_ica_anual(rutas["expo_anual_rubros"], "Combustibles y energía")
    impo = indec.leer_ica_anual(rutas["impo_anual_usos"], "Combustibles y lubricantes")
    anual = pd.DataFrame({
        "expo_total_musd": expo["total"], "impo_total_musd": impo["total"],
        "expo_cye_musd": expo["rubro"], "impo_cyl_musd": impo["rubro"],
    })
    anual["saldo_total_musd"] = anual["expo_total_musd"] - anual["impo_total_musd"]
    anual["saldo_cye_cyl_musd"] = anual["expo_cye_musd"] - anual["impo_cyl_musd"]
    anual["provisorio"] = expo["provisorio"] | impo["provisorio"]

    # Capítulo 27: se leen los cuadros del más viejo al más nuevo; cada año queda con el más nuevo.
    cap27 = {"expo": {}, "impo": {}}
    archivo, unidades = {}, []
    for flujo in ("expo", "impo"):
        for ruta in capitulos[flujo]:
            cuadro = indec.leer_capitulo_anual(ruta)
            for anio, valor in cuadro["capitulo27"].items():
                cap27[flujo][anio] = valor
                archivo[(flujo, anio)] = ruta.name
            for anio, total in cuadro["total"].items():
                cociente = total / anual.loc[anio, f"{flujo}_total_musd"]
                unidades.append({"archivo": ruta.name, "anio": anio, "total_cuadro": total,
                                 "total_oficial": anual.loc[anio, f"{flujo}_total_musd"], "cociente": cociente,
                                 "estado": "OK" if 0.8 <= cociente <= 1.25 else "REVISAR"})
    unidades = pd.DataFrame(unidades)
    if (unidades["estado"] != "OK").any():
        raise ValueError("Un cuadro por capítulo no está en millones de USD:\n"
                         + unidades[unidades["estado"] != "OK"].to_string())
    anual["expo_cap27_musd"] = pd.Series(cap27["expo"])
    anual["impo_cap27_musd"] = pd.Series(cap27["impo"])
    anual["fuente_cap27"] = [f"INDEC, {archivo[('expo', a)]} y {archivo[('impo', a)]}"
                             if ("expo", a) in archivo else None for a in anual.index]

    # Años sin cuadro anual por capítulo (antes de 2010): suma de los meses de la API. Antes de
    # 2018 la base de comercio exterior no tenía secreto estadístico, así que el total es completo.
    for anio in range(PRIMER_ANIO_NOTA, min(cap27["expo"])):
        meses = cap27_mensual.loc[str(anio)]
        if len(meses) != 12 or (meses["fuente"] != FUENTE_API).any():
            raise ValueError(f"{anio}: se esperaban 12 meses de la API")
        anual.loc[anio, ["expo_cap27_musd", "impo_cap27_musd"]] = meses[["expo_cap27_musd", "impo_cap27_musd"]].sum().values
        anual.loc[anio, "fuente_cap27"] = "Suma de los 12 meses de la API (no hay cuadro anual por capítulo)"

    anual["saldo_cap27_musd"] = anual["expo_cap27_musd"] - anual["impo_cap27_musd"]
    anual.index.name = "anio"
    return anual, unidades


# ---------------------------------------------------------------------------------------------
# 3. Gráficos y cifras para el texto
# ---------------------------------------------------------------------------------------------
COLUMNAS_CAP27 = ["expo_cap27_musd", "impo_cap27_musd", "saldo_cap27_musd"]


def etiqueta_acumulado(mes: pd.Timestamp, anio: int) -> str:
    return f"{anio} ene-{indec.MESES_ABREV[mes.month - 1].lower()}"


def armar_g1(anual: pd.DataFrame, ultimo: dict) -> pd.DataFrame:
    """Años completos (anual oficial) + mismo período acumulado del año anterior y del año en curso
    (acumulados oficiales del último informe)."""
    mes = ultimo["cap27"]["mes"]
    anio_completo = mes.year if mes.month == 12 else mes.year - 1
    if anio_completo not in anual.index or pd.isna(anual.loc[anio_completo, "saldo_cap27_musd"]):
        raise ValueError(f"Falta el anual oficial del capítulo 27 de {anio_completo}")

    g1 = anual.loc[PRIMER_ANIO_NOTA:anio_completo, COLUMNAS_CAP27].copy()
    g1.index = [str(a) for a in g1.index]
    if mes.month < 12:
        acumulado = ultimo["cap27"]["acumulado"]
        for anio, clave in ((mes.year - 1, "anterior"), (mes.year, "actual")):
            valores = acumulado[clave]
            g1.loc[etiqueta_acumulado(mes, anio)] = [valores["expo"], valores["impo"], valores["saldo"]]
    g1.index.name = "periodo"
    return g1


def armar_g2(cap27: pd.DataFrame, ica: pd.DataFrame) -> pd.DataFrame:
    """Saldo del capítulo 27 y saldo comercial de bienes, suma móvil de 12 meses."""
    g2 = pd.DataFrame({
        "saldo_cap27_12m_musd": cap27["saldo_cap27_musd"].rolling(12).sum(),
        "saldo_comercial_bienes_12m_musd": ica["saldo_total_musd"].rolling(12).sum(),
    })
    ultimo_comun = min(cap27.index.max(), ica.index.max())
    g2 = g2.loc[f"{PRIMER_ANIO_NOTA}-01-01":ultimo_comun]
    g2.index.name = "fecha"
    return g2


def armar_cifras_para_el_texto(anual: pd.DataFrame, ultimo: dict) -> pd.DataFrame:
    """Cifras citables, solo de anuales y acumulados oficiales (no se suman meses)."""
    mes = ultimo["cap27"]["mes"]
    acum27, acum1 = ultimo["cap27"]["acumulado"], ultimo["cuadro1"]
    fecha_informe = f"{ultimo['fecha_publicacion']:%d/%m/%Y}"
    anio_completo = mes.year - 1

    filas = []
    for anio in range(anio_completo - 2, anio_completo + 1):
        fila = anual.loc[anio]
        filas.append({
            "periodo": str(anio),
            "expo_cap27_musd": fila["expo_cap27_musd"], "impo_cap27_musd": fila["impo_cap27_musd"],
            "saldo_cap27_musd": fila["saldo_cap27_musd"], "saldo_comercial_bienes_musd": fila["saldo_total_musd"],
            "fuente": f"Anual oficial: {fila['fuente_cap27']}; exp_gr_80 e imp_uso_econ_80 (saldo de bienes)",
        })
    for anio, clave in ((mes.year - 1, "anterior"), (mes.year, "actual")):
        filas.append({
            "periodo": etiqueta_acumulado(mes, anio),
            "expo_cap27_musd": acum27[clave]["expo"], "impo_cap27_musd": acum27[clave]["impo"],
            "saldo_cap27_musd": acum27[clave]["saldo"], "saldo_comercial_bienes_musd": acum1[clave]["saldo"],
            "fuente": f"Acumulado oficial del informe ICA del {fecha_informe} (cuadro 8 y cuadro 1)",
        })
    # Últimos 12 meses = año completo anterior + acumulado del año en curso - mismo acumulado del
    # año anterior (por ejemplo: 2025 + ene-sep 2026 - ene-sep 2025). Todo sale de cifras oficiales.
    anio_anterior, acum_anio_anterior, acum_anio_actual = filas[2], filas[3], filas[4]
    filas.append({
        "periodo": f"12 meses a {indec.MESES_ABREV[mes.month - 1].lower()}-{mes.year}",
        **{col: anio_anterior[col] + acum_anio_actual[col] - acum_anio_anterior[col]
           for col in ["expo_cap27_musd", "impo_cap27_musd", "saldo_cap27_musd", "saldo_comercial_bienes_musd"]},
        "fuente": f"Derivado de oficiales: {anio_completo} + ene-{indec.MESES_ABREV[mes.month - 1].lower()} "
                  f"{mes.year} - ene-{indec.MESES_ABREV[mes.month - 1].lower()} {mes.year - 1}",
    })
    cifras = pd.DataFrame(filas).set_index("periodo")
    cifras.insert(4, "peso_saldo_cap27_pct", 100 * cifras["saldo_cap27_musd"] / cifras["saldo_comercial_bienes_musd"])
    return cifras


def guardar_png_g1(g1: pd.DataFrame, ruta: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 5))
    g1[["expo_cap27_musd", "impo_cap27_musd"]].plot.bar(ax=ax, width=0.8)
    ax.plot(range(len(g1)), g1["saldo_cap27_musd"], color="black", marker="o", label="saldo_cap27_musd")
    ax.axhline(0, color="grey", linewidth=0.8)
    ax.set_title("g1. Balanza comercial del capítulo 27 (millones de USD) - control rápido")
    ax.legend()
    fig.tight_layout()
    fig.savefig(ruta, dpi=100)
    plt.close(fig)


def guardar_png_g2(g2: pd.DataFrame, ruta: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 5))
    g2.plot(ax=ax)
    ax.axhline(0, color="grey", linewidth=0.8)
    ax.set_title("g2. Saldo del capítulo 27 vs. saldo comercial de bienes, 12 meses (millones de USD) - control rápido")
    fig.tight_layout()
    fig.savefig(ruta, dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------------------------------------
# 4. Controles y comparaciones
# ---------------------------------------------------------------------------------------------
def controles_generales(cap27, ica, anual, cuadros, ultimo) -> pd.DataFrame:
    resultados = []

    def anotar(control, ok, detalle):
        resultados.append({"control": control, "estado": "OK" if ok else "REVISAR", "detalle": detalle})

    for nombre, tabla in (("capítulo 27", cap27), ("rubros y usos", ica)):
        esperado = pd.date_range(tabla.index.min(), tabla.index.max(), freq="MS")
        faltan = esperado.difference(tabla.index)
        anotar(f"Serie mensual {nombre} sin meses faltantes", len(faltan) == 0,
               f"{tabla.index.min():%m/%Y} a {tabla.index.max():%m/%Y}; faltan: {list(faltan.strftime('%m/%Y'))}")

    dif = max(abs(c["cap27"][p]["expo"] - c["cap27"][p]["impo"] - c["cap27"][p]["saldo"])
              for c in cuadros for p in ("mes_actual", "mes_anterior"))
    anotar("Cuadros cap. 27: saldo = expo - impo", dif < 0.01, f"diferencia máxima {dif:.6f} MUSD")

    ok = ((cap27["expo_cap27_musd"] <= ica["expo_total_musd"].reindex(cap27.index).fillna(float("inf")))
          & (cap27["impo_cap27_musd"] <= ica["impo_total_musd"].reindex(cap27.index).fillna(float("inf")))
          & (cap27[["expo_cap27_musd", "impo_cap27_musd"]] >= 0).all(axis=1)).all()
    anotar("0 <= capítulo 27 <= total, todos los meses", ok, "exportaciones e importaciones")

    # La serie por rubros y usos tiene que coincidir con los anuales y con el acumulado del cuadro 1.
    completos = ica.groupby(ica.index.year).filter(lambda x: len(x) == 12)
    suma = completos.groupby(completos.index.year)[["expo_total_musd", "impo_total_musd", "expo_cye_musd", "impo_cyl_musd"]].sum()
    comunes = suma.index.intersection(anual.index)
    dif = (suma.loc[comunes] - anual.loc[comunes, suma.columns]).abs().max().max()
    anotar("Rubros y usos mensual = anuales oficiales (totales, CyE, CyL)", dif < 0.01,
           f"{comunes.min()}-{comunes.max()}; diferencia máxima {dif:.6f} MUSD")

    mes = ultimo["cap27"]["mes"]
    for clave, anio in (("actual", mes.year), ("anterior", mes.year - 1)):
        meses = ica.loc[f"{anio}-01-01":f"{anio}-{mes.month:02d}-01"]
        dif = max(abs(meses["expo_total_musd"].sum() - ultimo["cuadro1"][clave]["expo"]),
                  abs(meses["impo_total_musd"].sum() - ultimo["cuadro1"][clave]["impo"]))
        anotar(f"Rubros y usos ene-{mes.month:02d}/{anio} = acumulado del cuadro 1", dif < 0.01,
               f"diferencia máxima {dif:.6f} MUSD")
    return pd.DataFrame(resultados)


def control_publicados(cuadros: list[dict]) -> pd.DataFrame:
    """Lo que leemos de los Excel de cuadros vs. lo publicado en los informes (PDF)."""
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
        filas.append({"dato": dato, "valor_leido": round(valor, 2), "valor_publicado": publicado,
                      "diferencia": round(valor - publicado, 2),
                      "estado": "OK" if abs(valor - publicado) <= TOLERANCIA_MUSD else "REVISAR", "donde": donde})
    return pd.DataFrame(filas)


def control_suma_de_meses(cap27: pd.DataFrame, anual: pd.DataFrame, cuadros: list[dict]) -> pd.DataFrame:
    """Suma de los meses de la serie vs. anuales y acumulados oficiales. Con el último informe
    tiene que dar cero; con informes anteriores muestra cuánto revisó después el INDEC."""
    filas = []
    meses_por_anio = cap27.groupby(cap27.index.year).size()
    for anio in anual.index:
        if anio < PRIMER_ANIO_NOTA or meses_por_anio.get(anio, 0) != 12 or pd.isna(anual.loc[anio, "saldo_cap27_musd"]):
            continue
        suma = cap27.loc[str(anio), COLUMNAS_CAP27].sum()
        filas.append({"periodo": str(anio), "oficial": "anual", "fuente_oficial": anual.loc[anio, "fuente_cap27"],
                      **{f"{c}_suma_meses": suma[c] for c in COLUMNAS_CAP27},
                      **{f"{c}_oficial": anual.loc[anio, c] for c in COLUMNAS_CAP27}})
    for cuadro in cuadros:
        c27 = cuadro["cap27"]
        mes = c27["mes"]
        for anio, clave in ((mes.year, "actual"), (mes.year - 1, "anterior")):
            suma = cap27.loc[f"{anio}-01-01":f"{anio}-{mes.month:02d}-01", COLUMNAS_CAP27].sum()
            oficial = c27["acumulado"][clave]
            filas.append({"periodo": etiqueta_acumulado(mes, anio), "oficial": "acumulado",
                          "fuente_oficial": f"Informe ICA del {cuadro['fecha_publicacion']:%d/%m/%Y}",
                          **{f"{c}_suma_meses": suma[c] for c in COLUMNAS_CAP27},
                          "expo_cap27_musd_oficial": oficial["expo"], "impo_cap27_musd_oficial": oficial["impo"],
                          "saldo_cap27_musd_oficial": oficial["saldo"]})
    tabla = pd.DataFrame(filas)
    for c in COLUMNAS_CAP27:
        tabla[f"{c}_dif"] = tabla[f"{c}_suma_meses"] - tabla[f"{c}_oficial"]
    return tabla


def comparar_cye_cyl(anual: pd.DataFrame, ica: pd.DataFrame, ultimo: dict) -> pd.DataFrame:
    """Definición CyE - CyL (rubro y uso económico) vs. capítulo 27, anual y acumulado."""
    columnas = ["expo_cye_musd", "expo_cap27_musd", "impo_cyl_musd", "impo_cap27_musd",
                "saldo_cye_cyl_musd", "saldo_cap27_musd"]
    mes = ultimo["cap27"]["mes"]
    tabla = anual.loc[PRIMER_ANIO_NOTA:mes.year - 1, columnas].copy()
    tabla.index = [str(a) for a in tabla.index]
    for anio, clave in ((mes.year - 1, "anterior"), (mes.year, "actual")):
        meses = ica.loc[f"{anio}-01-01":f"{anio}-{mes.month:02d}-01"]
        acum = ultimo["cap27"]["acumulado"][clave]
        tabla.loc[etiqueta_acumulado(mes, anio)] = [
            meses["expo_cye_musd"].sum(), acum["expo"], meses["impo_cyl_musd"].sum(), acum["impo"],
            meses["saldo_cye_cyl_musd"].sum(), acum["saldo"]]
    tabla["dif_saldo_musd"] = tabla["saldo_cye_cyl_musd"] - tabla["saldo_cap27_musd"]
    tabla["dif_saldo_pct"] = 100 * tabla["dif_saldo_musd"] / tabla["saldo_cap27_musd"].abs()
    tabla.index.name = "periodo"
    return tabla


def comparar_api_con_informes(api: pd.DataFrame, cap27: pd.DataFrame) -> pd.DataFrame:
    """Meses que están en la API y también en un informe: diferencia por revisiones."""
    comunes = api.index.intersection(cap27[cap27["fuente"] != FUENTE_API].index)
    tabla = pd.DataFrame({
        "expo_api": api.loc[comunes, "expo_cap27_musd"], "expo_informe": cap27.loc[comunes, "expo_cap27_musd"],
        "impo_api": api.loc[comunes, "impo_cap27_musd"], "impo_informe": cap27.loc[comunes, "impo_cap27_musd"],
        "fuente_informe": cap27.loc[comunes, "fuente"]})
    tabla["dif_expo"] = tabla["expo_api"] - tabla["expo_informe"]
    tabla["dif_impo"] = tabla["impo_api"] - tabla["impo_informe"]
    tabla.index.name = "fecha"
    return tabla


def comparar_publicado_con_derivado(cap27: pd.DataFrame, cuadros: list[dict]) -> pd.DataFrame:
    """Cada mes tal como lo publicó el informe más reciente que lo trae vs. el mes derivado de los
    acumulados. La diferencia es la parte de las revisiones posteriores que cae en ese mes."""
    publicados = meses_publicados(cuadros)
    comunes = publicados.index.intersection(cap27.index)
    tabla = pd.DataFrame({
        "saldo_publicado": publicados.loc[comunes, "saldo"], "informe_publicado": publicados.loc[comunes, "informe"],
        "saldo_derivado": cap27.loc[comunes, "saldo_cap27_musd"]})
    tabla["dif_saldo"] = tabla["saldo_derivado"] - tabla["saldo_publicado"]
    tabla.index.name = "fecha"
    return tabla


def contrastar_anuales(anual: pd.DataFrame, informes_todos: pd.DataFrame, anios: list[int]) -> tuple[pd.DataFrame, list[dict]]:
    """Anual oficial del capítulo 27 vs. lo publicado en los informes ICA de diciembre:
    primera publicación (informe de enero del año siguiente, columna del año en curso) y versión
    revisada un año después (informe de enero de dos años después, columna del año anterior)."""
    filas, registros = [], []
    for anio in anios:
        for version, anio_publicacion, clave in (("primera publicación", anio + 1, "actual"),
                                                 ("revisada un año después", anio + 2, "anterior")):
            fila = {"anio": anio, "version": version}
            candidatos = informes_todos[(informes_todos["fecha_publicacion"].dt.year == anio_publicacion)
                                        & (informes_todos["fecha_publicacion"].dt.month == 1)]
            if candidatos.empty:
                filas.append({**fila, "estado": "TODAVIA NO PUBLICADO"})
                continue
            informe = candidatos.iloc[0]
            fila["informe"] = f"{informe.fecha_publicacion:%d/%m/%Y}"
            ruta, registro = indec.descargar_archivo(informe.url_cuadros)
            registros.append(registro)
            try:
                c27 = indec.leer_cuadro_capitulo27(ruta)
            except (ValueError, StopIteration):
                filas.append({**fila, "estado": "EL INFORME NO TRAE EL CUADRO DEL CAPITULO 27"})
                continue
            if c27["mes"] != pd.Timestamp(anio_publicacion - 1, 12, 1):
                raise ValueError(f"{ruta.name}: se esperaba el informe de diciembre de {anio_publicacion - 1}")
            publicado = c27["acumulado"][clave]
            for c in ("expo", "impo", "saldo"):
                fila[f"{c}_informe"] = publicado[c]
                fila[f"{c}_anual_oficial"] = anual.loc[anio, f"{c}_cap27_musd"]
                fila[f"dif_{c}"] = anual.loc[anio, f"{c}_cap27_musd"] - publicado[c]
            fila["anual_oficial_de"] = anual.loc[anio, "fuente_cap27"]
            fila["estado"] = "OK" if abs(fila["dif_saldo"]) <= TOLERANCIA_MUSD else "REVISION POSTERIOR DEL INDEC"
            filas.append(fila)
    return pd.DataFrame(filas), registros


# ---------------------------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------------------------
def main():
    sys.stdout.reconfigure(encoding="utf-8")  # para que la consola de Windows muestre bien las tildes
    GRAFICOS.mkdir(exist_ok=True)
    VALIDACION.mkdir(exist_ok=True)

    datos = bajar_datos()
    cuadros = datos["cuadros"]
    ultimo = max(cuadros, key=lambda c: c["fecha_publicacion"])

    cap27 = armar_cap27_mensual(datos["api"], cuadros)
    ica = armar_ica_mensual(datos["rubros_usos"])
    anual, control_unidades = armar_anual(datos["rutas"], datos["capitulos"], cap27)

    # Series procesadas (se suben al repositorio).
    cap27.to_csv(PROCESADOS / "ica_cap27_mensual.csv", float_format="%.3f", date_format="%Y-%m-%d")
    ica.to_csv(PROCESADOS / "ica_mensual.csv", float_format="%.3f", date_format="%Y-%m-%d")
    anual.to_csv(PROCESADOS / "ica_anual.csv", float_format="%.3f")

    # Gráficos: CSV para Datawrapper (punto decimal, coma separadora, una fila por período) y PNG de control.
    g1 = armar_g1(anual, ultimo)
    g1.to_csv(GRAFICOS / "g1_balanza_energetica_anual.csv", float_format="%.1f")
    guardar_png_g1(g1, GRAFICOS / "g1_balanza_energetica_anual.png")
    g2 = armar_g2(cap27, ica)
    g2.to_csv(GRAFICOS / "g2_saldo_energetico_vs_total_12m.csv", float_format="%.1f", date_format="%Y-%m-%d")
    guardar_png_g2(g2, GRAFICOS / "g2_saldo_energetico_vs_total_12m.png")

    # Cifras para citar en el texto (solo oficiales).
    cifras = armar_cifras_para_el_texto(anual, ultimo)
    cifras.to_csv(CARPETA_NOTA / "cifras_para_el_texto.csv", float_format="%.1f")

    # Controles, comparaciones y trazabilidad.
    generales = controles_generales(cap27, ica, anual, cuadros, ultimo)
    publicados = control_publicados(cuadros)
    suma_meses = control_suma_de_meses(cap27, anual, cuadros)
    cye_cyl = comparar_cye_cyl(anual, ica, ultimo)
    api_vs_informes = comparar_api_con_informes(datos["api"], cap27)
    publicado_vs_derivado = comparar_publicado_con_derivado(cap27, cuadros)
    anio_completo = ultimo["cap27"]["mes"].year - 1
    anual_vs_informes, regs = contrastar_anuales(anual, datos["informes_todos"], list(range(anio_completo - 2, anio_completo + 1)))
    datos["registros"] += regs

    ultimo_acumulado = suma_meses[suma_meses["fuente_oficial"] == f"Informe ICA del {ultimo['fecha_publicacion']:%d/%m/%Y}"]
    dif_ultimo = ultimo_acumulado["saldo_cap27_musd_dif"].abs().max()
    generales = pd.concat([generales, pd.DataFrame([
        {"control": "Unidades de los cuadros por capítulo (total del cuadro / total oficial)",
         "estado": "OK" if (control_unidades["estado"] == "OK").all() else "REVISAR",
         "detalle": f"cociente entre {control_unidades['cociente'].min():.4f} y {control_unidades['cociente'].max():.4f}"},
        {"control": "Suma de los meses = acumulados oficiales del último informe (año en curso y anterior)",
         "estado": "OK" if dif_ultimo < 0.01 else "REVISAR", "detalle": f"diferencia máxima {dif_ultimo:.6f} MUSD"},
    ])], ignore_index=True)
    generales.to_csv(VALIDACION / "controles.csv", index=False)
    control_unidades.to_csv(VALIDACION / "control_unidades_cuadros_capitulos.csv", index=False, float_format="%.4f")
    publicados.to_csv(VALIDACION / "control_valores_publicados.csv", index=False)
    suma_meses.to_csv(VALIDACION / "cap27_suma_meses_vs_oficial.csv", index=False, float_format="%.2f")
    cye_cyl.to_csv(VALIDACION / "comparacion_cye_cyl_vs_cap27.csv", float_format="%.1f")
    api_vs_informes.to_csv(VALIDACION / "cap27_api_vs_informes.csv", float_format="%.2f", date_format="%Y-%m-%d")
    publicado_vs_derivado.to_csv(VALIDACION / "cap27_mes_publicado_vs_derivado.csv", float_format="%.2f", date_format="%Y-%m-%d")
    anual_vs_informes.to_csv(VALIDACION / "cap27_anual_vs_informes.csv", index=False, float_format="%.2f")
    datos["informes"].to_csv(VALIDACION / "informes_ica_usados.csv", index=False, date_format="%Y-%m-%d")
    datos["metadatos"].to_csv(VALIDACION / "metadatos_series_api.csv", index=False)
    guardar_registro(datos["registros"], VALIDACION / "descargas.csv")

    # Resumen en pantalla.
    pd.set_option("display.width", 220)
    print(f"\nCapítulo 27 mensual: {cap27.index.min():%m/%Y} a {cap27.index.max():%m/%Y}; "
          f"meses de la API: {(cap27['fuente'] == FUENTE_API).sum()}, de informes: {(cap27['fuente'] != FUENTE_API).sum()} "
          f"(desde {cap27[cap27['fuente'] != FUENTE_API].index.min():%m/%Y})")
    print("\nControles generales:\n" + generales.to_string(index=False))
    print("\nValores leídos vs. publicados:\n" + publicados[["dato", "valor_leido", "valor_publicado", "diferencia", "estado"]].to_string(index=False))
    print("\nCifras para el texto (solo oficiales):\n" + cifras.drop(columns="fuente").round(1).to_string())
    print("\nSuma de meses vs. acumulado oficial (último informe):\n"
          + ultimo_acumulado[["periodo", "saldo_cap27_musd_suma_meses", "saldo_cap27_musd_oficial", "saldo_cap27_musd_dif"]].round(1).to_string(index=False))
    print("\nAnual oficial del capítulo 27 vs. informes de diciembre (saldo):\n"
          + anual_vs_informes.reindex(columns=["anio", "version", "informe", "saldo_informe", "saldo_anual_oficial", "dif_saldo", "estado"]).round(1).to_string(index=False))

    hay_problemas = (generales["estado"] != "OK").any() or (publicados["estado"] != "OK").any()
    print("\nRESULTADO:", "HAY CONTROLES PARA REVISAR" if hay_problemas else "todos los controles OK")


if __name__ == "__main__":
    main()
