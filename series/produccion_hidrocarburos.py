"""
Series de producción de petróleo y gas de la Argentina (bloque Energía).

Ubicación provisoria: la carpeta series/ guarda los armadores de series genéricas (no atadas a una
nota) hasta que se defina la arquitectura del repositorio.

Qué hace:
    1. Serie mensual nacional de petróleo y gas por subtipo de recurso (convencional, shale y tight)
       con las series agregadas oficiales de la Secretaría de Energía (SE) "por cuenca y sub tipo de
       recurso (Capítulo IV)", desde enero de 2006 hasta el último mes publicado.
       - Convencional = total - shale - tight. Para la SE, no convencional = shale + tight: su columna
         de participación no convencional es (shale + tight) / total (control "no convencional").
    2. Serie mensual de Vaca Muerta desde enero de 2010: suma de los pozos con formación productiva
       (formprod) VMUT y tipo de recurso NO CONVENCIONAL del archivo por pozo de pozos no convencionales.
    3. Controles (en datos/validacion/):
       - internos de las series agregadas (meses, vacíos, unidades, factor, subtipos, cuencas);
       - archivo no convencional vs. serie agregada: shale y tight, todos los meses, y lista de los
         meses que no cierran (en volumen, en promedio diario y en %);
       - evidencia de la regla de la SE "pozo no convencional sin subtipo = tight";
       - cobertura del archivo no convencional vs. archivos anuales completos (ANIOS_COBERTURA), y
         esos anuales vs. la serie agregada (total, shale y tight);
       - corte: ninguna serie puede tener meses posteriores al último mes completo de la fuente
         oficial (el último mes de la serie agregada); si pasa, el script se detiene;
       - versiones: serie agregada vs. archivo anual de 2026 (más reciente), por mes, y registros
         cargados después de la serie agregada;
       - primera difusión vs. dato vigente (sin aprobar ni rechazar: se muestra la revisión).
    Cada archivo crudo se guarda también como versión (fecha de publicación + hash) en
    datos/crudos/secretaria_energia/versiones/, sin pisar las anteriores; el registro queda en
    datos/validacion/versiones_crudos.csv.

Unidades:
    - petróleo: m3 del mes, m3/d (m3 ÷ días del mes) y kbbl/d (m3 × 6,28981 ÷ días del mes ÷ 1.000);
    - gas: miles de m3 del mes y MMm3/d (miles de m3 ÷ días del mes ÷ 1.000).

Decisiones pendientes (no se toman acá): promedio anual; corte común o último dato disponible;
    qué hacer con los meses en que el archivo no convencional no cubre todo (columna
    control_cobertura de la serie de Vaca Muerta).

Fuentes: SE, datos.energia.gob.ar (detalle en scripts/secretaria_energia.py).

Genera:
    - datos/procesados/produccion_petroleo_gas_mensual.csv
    - datos/procesados/produccion_vaca_muerta_mensual.csv
    - datos/validacion/produccion_controles.csv
    - datos/validacion/produccion_no_convencional_vs_serie.csv
    - datos/validacion/produccion_regla_sin_subtipo.csv
    - datos/validacion/produccion_meses_que_no_cierran.csv
    - datos/validacion/produccion_cobertura_no_convencional.csv
    - datos/validacion/produccion_anuales_vs_serie.csv
    - datos/validacion/produccion_versiones_2026.csv
    - datos/validacion/produccion_vs_primera_difusion.csv
    - datos/validacion/descargas_produccion.csv

Uso (desde la raíz del repositorio):
    .venv/Scripts/python series/produccion_hidrocarburos.py
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))  # para poder importar scripts/ al correr este archivo directamente

import pandas as pd

from scripts import secretaria_energia as se
from scripts.descargas import PROCESADOS, guardar_registro

VALIDACION = RAIZ / "datos" / "validacion"

BARRILES_POR_M3 = 6.28981  # el mismo factor que usa la SE en su columna kbbl_diario (ver controles)
SUBTIPOS = ["total", "convencional", "shale", "tight"]
DESDE_VACA_MUERTA = "2010-01-01"
# Años en que se contrastan los archivos anuales completos (todos los pozos) contra el archivo no
# convencional y contra la serie agregada. 2015: uno de 2010-2015, con un mes que no cierra (06/2015);
# 2024: el año del hueco de 09/2024; 2026: el más reciente.
ANIOS_COBERTURA = [2015, 2024, 2026]
# Fecha de la serie agregada usada (última actualización en el portal). Sirve para identificar los
# registros por pozo cargados después.
FECHA_SERIE_AGREGADA = "2026-10-21"

# Primera difusión de cada cifra, con su fuente (verificada en la página el 18/11/2026; detalle en
# datos/validacion/produccion_informe_validacion.md). (serie, mes, valor, unidad, fuente)
COMUNICADO_JULIO_2026 = ("Comunicado oficial, Ministerio de Economía - Energía, 24/08/2026: https://www.argentina.gob.ar/"
                         "noticias/la-produccion-de-petroleo-registro-otro-mes-de-crecimiento-en-julio")
CONFERENCIA_30_06_2026 = ("Conferencia de prensa del vocero presidencial, 30/06/2026 (transcripción oficial): https://www.casarosada.gob.ar/"
                          "informacion/conferencias/51305-conferencia-de-prensa-del-vocero-presidencial-adrian-ravier-desde-casa-rosada-30-06-2026")
PRIMERA_DIFUSION = [
    ("petroleo_total", "2025-10", 859.5, "kbbl/d",
     "Post en X de la Secretaría de Energía (@Energia_Ar), 20/11/2025: https://x.com/Energia_Ar/status/1991579025807143398 "
     "(leído embebido en https://www.memo.com.ar/economia/record-argentina-octubre-2025-petroleo-produccion/; sin comunicado en argentina.gob.ar)"),
    ("petroleo_total", "2025-12", 868.7, "kbbl/d",
     "Post en X del Ministerio de Economía (@MinEconomia_Ar), 22/01/2026, '868.712 barriles por día': "
     "https://x.com/MinEconomia_Ar/status/2014291960077725735 (leído embebido en "
     "https://www.lacapitalmdp.com/argentina-alcanzo-un-record-en-la-produccion-de-petroleo/; sin comunicado en argentina.gob.ar)"),
    ("petroleo_total", "2026-05", 903.7, "kbbl/d", CONFERENCIA_30_06_2026),
    ("gas_total", "2026-05", 156.6, "MMm3/d", CONFERENCIA_30_06_2026 + " (agregada por Code: aparece en la misma fuente)"),
    ("petroleo_total", "2026-07", 916.2, "kbbl/d", COMUNICADO_JULIO_2026),
    ("gas_total", "2026-07", 158.8, "MMm3/d", COMUNICADO_JULIO_2026),
    ("petroleo_vaca_muerta", "2026-07", 643.1, "kbbl/d", COMUNICADO_JULIO_2026),
    ("petroleo_total", "2026-09", 973.7, "kbbl/d",
     "Sin comunicado oficial de primera difusión. Mención oficial posterior, Ministerio de Economía, 11/11/2026: "
     "https://www.argentina.gob.ar/noticias/ya-esta-abierta-la-inscripcion-para-la-segunda-ronda-de-negocios-rigi-con-foco-en. "
     "Prensa del 21/10/2026 (DolarHoy) la atribuye a la Secretaría de Energía"),
    ("gas_total", "2026-09", 143.1, "MMm3/d",
     "Sin fuente oficial encontrada. Solo prensa: DolarHoy, 21/10/2026 (sin atribución) e iProfesional "
     "(informe de RICSA con datos de la Secretaría de Energía)"),
]


# ---------------------------------------------------------------------------------------------
# 1. Series
# ---------------------------------------------------------------------------------------------
def armar_nacional(petroleo: pd.DataFrame, gas: pd.DataFrame) -> pd.DataFrame:
    """Petróleo y gas por subtipo de recurso: volumen del mes y promedio diario."""
    dias = pd.Series(petroleo.index.days_in_month, index=petroleo.index)
    volumen_petroleo = {"total": petroleo["total"], "shale": petroleo["shale"], "tight": petroleo["tight"]}
    volumen_petroleo["convencional"] = petroleo["total"] - petroleo["shale"] - petroleo["tight"]
    volumen_gas = {"total": gas["produccion_gas_natural_total"], "shale": gas["produccion_shale_gas"],
                   "tight": gas["produccion_tight_gas"]}
    volumen_gas["convencional"] = volumen_gas["total"] - volumen_gas["shale"] - volumen_gas["tight"]

    serie = pd.DataFrame({"dias_del_mes": dias})
    for s in SUBTIPOS:
        serie[f"petroleo_{s}_m3_mes"] = volumen_petroleo[s]
    for s in SUBTIPOS:
        serie[f"petroleo_{s}_m3_d"] = volumen_petroleo[s] / dias
    for s in SUBTIPOS:
        serie[f"petroleo_{s}_kbbl_d"] = volumen_petroleo[s] * BARRILES_POR_M3 / dias / 1000
    for s in SUBTIPOS:
        serie[f"gas_{s}_miles_m3_mes"] = volumen_gas[s]
    for s in SUBTIPOS:
        serie[f"gas_{s}_mm3_d"] = volumen_gas[s] / dias / 1000
    return serie


def comparar_no_convencional_con_serie(pozos_nc: pd.DataFrame, petroleo: pd.DataFrame, gas: pd.DataFrame) -> pd.DataFrame:
    """Suma mensual del archivo no convencional por subtipo vs. la serie agregada, todos los meses.
    La SE cuenta como tight a los pozos no convencionales sin subtipo: se muestran las dos sumas."""
    sub = pozos_nc["sub_tipo_recurso"].fillna("SIN_SUBTIPO")
    suma = pozos_nc.assign(sub=sub).pivot_table(index="fecha", columns="sub", values=["prod_pet", "prod_gas"],
                                                aggfunc="sum").fillna(0)
    tabla = pd.DataFrame({
        "petroleo_shale_archivo_nc": suma[("prod_pet", "SHALE")], "petroleo_shale_serie": petroleo["shale"],
        "petroleo_tight_archivo_nc": suma[("prod_pet", "TIGHT")], "petroleo_sin_subtipo_archivo_nc": suma[("prod_pet", "SIN_SUBTIPO")],
        "petroleo_tight_serie": petroleo["tight"],
        "gas_shale_archivo_nc": suma[("prod_gas", "SHALE")], "gas_shale_serie": gas["produccion_shale_gas"],
        "gas_tight_archivo_nc": suma[("prod_gas", "TIGHT")], "gas_sin_subtipo_archivo_nc": suma[("prod_gas", "SIN_SUBTIPO")],
        "gas_tight_serie": gas["produccion_tight_gas"],
        "pozos_shale_archivo_nc": pozos_nc[pozos_nc["sub_tipo_recurso"] == "SHALE"].groupby("fecha")["idpozo"].nunique(),
    }).fillna({"pozos_shale_archivo_nc": 0})
    for producto in ("petroleo", "gas"):
        tabla[f"{producto}_shale_dif"] = tabla[f"{producto}_shale_archivo_nc"] - tabla[f"{producto}_shale_serie"]
        tabla[f"{producto}_tight_dif"] = (tabla[f"{producto}_tight_archivo_nc"] + tabla[f"{producto}_sin_subtipo_archivo_nc"]
                                          - tabla[f"{producto}_tight_serie"])
    tabla.index.name = "fecha"
    return tabla


def evidencia_regla_sin_subtipo(comparacion: pd.DataFrame) -> pd.DataFrame:
    """Evidencia de la regla "no convencional sin subtipo = tight": en los meses con producción de
    pozos no convencionales sin subtipo, compara tres hipótesis contra la serie de la SE:
    (1) esos pozos no se cuentan; (2) se cuentan como tight; (3) se cuentan como shale."""
    c = comparacion[(comparacion["petroleo_sin_subtipo_archivo_nc"] != 0) | (comparacion["gas_sin_subtipo_archivo_nc"] != 0)]
    filas = []
    for fecha, f in c.iterrows():
        fila = {"fecha": fecha}
        for p in ("petroleo", "gas"):
            sin = f[f"{p}_sin_subtipo_archivo_nc"]
            fila[f"{p}_sin_subtipo"] = sin
            fila[f"{p}_tight_dif_si_no_se_cuentan"] = f[f"{p}_tight_archivo_nc"] - f[f"{p}_tight_serie"]
            fila[f"{p}_tight_dif_si_son_tight"] = f[f"{p}_tight_archivo_nc"] + sin - f[f"{p}_tight_serie"]
            fila[f"{p}_shale_dif_si_son_shale"] = f[f"{p}_shale_archivo_nc"] + sin - f[f"{p}_shale_serie"]
        filas.append(fila)
    return pd.DataFrame(filas).set_index("fecha")


def meses_que_no_cierran(comparacion: pd.DataFrame) -> pd.DataFrame:
    """Meses en que el archivo no convencional (con la regla de tight) no reproduce la serie de la SE,
    con la diferencia en volumen, en promedio diario (kbbl/d o MMm3/d) y en % de la serie."""
    filas = []
    for fecha, f in comparacion.iterrows():
        dias = fecha.days_in_month
        for producto, unidad in (("petroleo", "kbbl/d"), ("gas", "MMm3/d")):
            for subtipo in ("shale", "tight"):
                dif = f[f"{producto}_{subtipo}_dif"]
                if abs(dif) > 0.01:
                    serie = f[f"{producto}_{subtipo}_serie"]
                    diaria = dif * BARRILES_POR_M3 / dias / 1000 if producto == "petroleo" else dif / dias / 1000
                    filas.append({"fecha": fecha, "producto": producto, "subtipo": subtipo,
                                  "dif_volumen": dif, "unidad_volumen": "m3" if producto == "petroleo" else "miles de m3",
                                  "dif_diaria": diaria, "unidad_diaria": unidad, "dif_pct_de_la_serie": 100 * dif / serie,
                                  "pozos_shale_archivo_nc": f["pozos_shale_archivo_nc"]})
    return pd.DataFrame(filas)


def anual_vs_serie(anual: pd.DataFrame, petroleo: pd.DataFrame, gas: pd.DataFrame, anio: int,
                   ultimo_mes_completo: pd.Timestamp) -> pd.DataFrame:
    """Archivo anual completo (todos los pozos) vs. serie agregada, por mes: total, shale y tight
    (tight = TIGHT + no convencional sin subtipo, la regla de la SE). Sirve para saber si un faltante
    está en los datos por pozo en general o solo en el archivo no convencional."""
    a = anual[anual["fecha"] <= ultimo_mes_completo]
    nc = a[a["tipo_de_recurso"] == "NO CONVENCIONAL"]
    shale = nc[nc["sub_tipo_recurso"] == "SHALE"]
    tight = nc[nc["sub_tipo_recurso"] != "SHALE"]  # TIGHT + sin subtipo
    tabla = pd.DataFrame({
        "petroleo_total_anual": a.groupby("fecha")["prod_pet"].sum(), "petroleo_total_serie": petroleo["total"],
        "petroleo_shale_anual": shale.groupby("fecha")["prod_pet"].sum(), "petroleo_shale_serie": petroleo["shale"],
        "petroleo_tight_anual": tight.groupby("fecha")["prod_pet"].sum(), "petroleo_tight_serie": petroleo["tight"],
        "gas_total_anual": a.groupby("fecha")["prod_gas"].sum(), "gas_total_serie": gas["produccion_gas_natural_total"],
        "gas_shale_anual": shale.groupby("fecha")["prod_gas"].sum(), "gas_shale_serie": gas["produccion_shale_gas"],
        "pozos_shale_anual": shale.groupby("fecha")["idpozo"].nunique(),
    })
    tabla = tabla[tabla.index.year == anio]
    for c in ("petroleo_total", "petroleo_shale", "petroleo_tight", "gas_total", "gas_shale"):
        tabla[f"{c}_dif"] = tabla[f"{c}_anual"] - tabla[f"{c}_serie"]
    dias = pd.Series(tabla.index.days_in_month, index=tabla.index)
    tabla["petroleo_total_dif_kbbl_d"] = tabla["petroleo_total_dif"] * BARRILES_POR_M3 / dias / 1000
    tabla["petroleo_shale_dif_kbbl_d"] = tabla["petroleo_shale_dif"] * BARRILES_POR_M3 / dias / 1000
    tabla.insert(0, "anio_contrastado", anio)
    tabla.index.name = "fecha"
    return tabla


def verificar_corte(series: dict[str, pd.DataFrame], ultimo_mes_completo: pd.Timestamp) -> None:
    """Impide que un mes posterior al último mes completo de la fuente oficial entre a una serie.
    El último mes completo es el último mes de la serie agregada que publica la SE: los archivos
    por pozo traen además meses parciales (por ejemplo, 10/2026 en el anual de 2026 del 18/11)."""
    for nombre, serie in series.items():
        if serie.index.max() > ultimo_mes_completo:
            raise ValueError(f"{nombre} llega a {serie.index.max():%m/%Y}, después del último mes completo de la "
                             f"fuente oficial ({ultimo_mes_completo:%m/%Y})")


def cobertura(pozos_nc: pd.DataFrame, anual: pd.DataFrame, anio: int, ultimo_mes_completo: pd.Timestamp) -> pd.DataFrame:
    """Cobertura del archivo no convencional vs. un archivo anual completo, por mes y solo hasta el
    último mes completo de la fuente oficial: pozo-mes NO CONVENCIONAL que están en uno y no en el
    otro (huecos) y volúmenes distintos (revisiones)."""
    anual_nc = anual[(anual["tipo_de_recurso"] == "NO CONVENCIONAL") & (anual["fecha"] <= ultimo_mes_completo)]
    nc = pozos_nc[pozos_nc["anio"] == anio]
    cruce = anual_nc.merge(nc, on=["idpozo", "fecha"], how="outer", suffixes=("_anual", "_nc"), indicator=True)
    cruce = cruce.fillna({c: 0 for c in ("prod_pet_anual", "prod_pet_nc", "prod_gas_anual", "prod_gas_nc")})
    cruce["pet_distinto"] = (cruce["_merge"] == "both") & ((cruce["prod_pet_anual"] - cruce["prod_pet_nc"]).abs() > 0.001)
    tabla = cruce.groupby("fecha").agg(
        pozo_mes_en_los_dos=("_merge", lambda x: (x == "both").sum()),
        pozo_mes_solo_en_anual=("_merge", lambda x: (x == "left_only").sum()),
        pozo_mes_solo_en_no_convencional=("_merge", lambda x: (x == "right_only").sum()),
        pozo_mes_con_petroleo_distinto=("pet_distinto", "sum"),
        petroleo_m3_anual=("prod_pet_anual", "sum"), petroleo_m3_no_convencional=("prod_pet_nc", "sum"),
        gas_miles_m3_anual=("prod_gas_anual", "sum"), gas_miles_m3_no_convencional=("prod_gas_nc", "sum"))
    tabla["dif_petroleo_m3"] = tabla["petroleo_m3_no_convencional"] - tabla["petroleo_m3_anual"]
    tabla["dif_gas_miles_m3"] = tabla["gas_miles_m3_no_convencional"] - tabla["gas_miles_m3_anual"]
    tabla.insert(0, "anio_contrastado", anio)
    return tabla


def armar_vaca_muerta(pozos_nc: pd.DataFrame, comparacion: pd.DataFrame, ultimo_mes_completo: pd.Timestamp) -> pd.DataFrame:
    """Vaca Muerta: formprod VMUT y tipo de recurso NO CONVENCIONAL, desde enero de 2010 hasta el
    último mes completo de la fuente oficial. La columna control_cobertura marca los meses en que
    la suma de shale del archivo no convencional no coincide con la serie agregada."""
    vm = pozos_nc[(pozos_nc["formprod"] == "VMUT") & (pozos_nc["tipo_de_recurso"] == "NO CONVENCIONAL")]
    vm = vm[(vm["fecha"] >= DESDE_VACA_MUERTA) & (vm["fecha"] <= ultimo_mes_completo)]
    serie = vm.groupby("fecha").agg(petroleo_m3_mes=("prod_pet", "sum"), gas_miles_m3_mes=("prod_gas", "sum"),
                                    pozos_con_registro=("idpozo", "nunique"))
    serie = serie.reindex(pd.date_range(DESDE_VACA_MUERTA, min(pozos_nc["fecha"].max(), ultimo_mes_completo), freq="MS"))
    serie.index.name = "fecha"
    dias = pd.Series(serie.index.days_in_month, index=serie.index)
    serie.insert(0, "dias_del_mes", dias)
    serie["petroleo_m3_d"] = serie["petroleo_m3_mes"] / dias
    serie["petroleo_kbbl_d"] = serie["petroleo_m3_mes"] * BARRILES_POR_M3 / dias / 1000
    serie["gas_mm3_d"] = serie["gas_miles_m3_mes"] / dias / 1000
    dif = comparacion.reindex(serie.index)["petroleo_shale_dif"]
    serie["control_cobertura"] = ["OK" if abs(d) < 0.01 else
                                  f"REVISAR: el archivo no convencional suma {d:,.1f} m3 de petróleo shale distinto de la serie agregada"
                                  for d in dif]
    columnas = ["dias_del_mes", "petroleo_m3_mes", "petroleo_m3_d", "petroleo_kbbl_d", "gas_miles_m3_mes",
                "gas_mm3_d", "pozos_con_registro", "control_cobertura"]
    return serie[columnas]


# ---------------------------------------------------------------------------------------------
# 2. Controles
# ---------------------------------------------------------------------------------------------
def controles(petroleo, gas, nacional, comparacion, regla, coberturas, anuales_vs, anual_2026, series, ultimo_mes_completo) -> pd.DataFrame:
    resultados = []

    def anotar(control, estado, detalle):
        resultados.append({"control": control, "estado": estado, "detalle": detalle})

    def ok(condicion):
        return "OK" if condicion else "REVISAR"

    dias = pd.Series(petroleo.index.days_in_month, index=petroleo.index)
    for nombre, tabla in (("petróleo", petroleo), ("gas", gas)):
        esperado = pd.date_range(tabla.index.min(), tabla.index.max(), freq="MS")
        anotar(f"Serie agregada de {nombre}: sin meses faltantes ni duplicados",
               ok(len(esperado.difference(tabla.index)) == 0 and not tabla.index.duplicated().any()),
               f"{tabla.index.min():%m/%Y} a {tabla.index.max():%m/%Y}, {len(tabla)} meses")
        numeros = tabla.select_dtypes("number")
        anotar(f"Serie agregada de {nombre}: sin vacíos ni negativos",
               ok(not numeros.isna().any().any() and not (numeros < 0).any().any()), "")

    # Unidades: se deducen de las columnas diarias que publica la propia SE.
    dif = (petroleo["total_diario"] - petroleo["total"] / dias).abs().max()
    anotar("Unidades petróleo: total_diario de la SE = total / días (total en m3 por mes)", ok(dif < 0.001),
           f"diferencia máxima {dif:.6f} m3/d")
    dif = (petroleo["kbbl_diario"] - petroleo["total"] * BARRILES_POR_M3 / dias / 1000).abs().max()
    anotar(f"Factor: kbbl_diario de la SE = m3/d × {BARRILES_POR_M3} / 1.000", ok(dif < 0.001), f"diferencia máxima {dif:.6f} kbbl/d")
    dif = (gas["produccion_gas_natural_total_diario"] - gas["produccion_gas_natural_total"] / dias / 1000).abs().max()
    anotar("Unidades gas: total_diario de la SE = total / días / 1.000 (total en miles de m3 por mes, diario en MMm3/d)",
           ok(dif < 0.001), f"diferencia máxima {dif:.6f} MMm3/d")

    # Subtipos.
    dif_p = (petroleo["part_no_conv"] - 100 * (petroleo["shale"] + petroleo["tight"]) / petroleo["total"]).abs().max()
    dif_g = (gas["participacion_no_convencional"] - 100 * (gas["produccion_shale_gas"] + gas["produccion_tight_gas"])
             / gas["produccion_gas_natural_total"]).abs().max()
    anotar("No convencional de la SE = shale + tight (participación publicada vs. (shale + tight) / total)",
           ok(max(dif_p, dif_g) < 0.001), f"diferencia máxima {max(dif_p, dif_g):.6f} puntos porcentuales")
    anotar("Convencional (total - shale - tight) >= 0, todos los meses",
           ok((nacional[["petroleo_convencional_m3_mes", "gas_convencional_miles_m3_mes"]] >= 0).all().all()), "petróleo y gas")
    # Qué pozos quedan en el convencional (total - shale - tight): se mira en el archivo anual 2026,
    # en los meses en que coincide con la serie agregada (la serie viene redondeada: tolerancia 0,5).
    a = anual_2026[anual_2026["fecha"] <= petroleo.index.max()]
    iguales = (a.groupby("fecha")["prod_pet"].sum() - petroleo["total"]).dropna().abs() < 0.5
    meses = iguales[iguales].index
    for producto, col_pozos, col_serie in (("petróleo", "prod_pet", "petroleo_convencional_m3_mes"),
                                           ("gas", "prod_gas", "gas_convencional_miles_m3_mes")):
        resto = a[(a["tipo_de_recurso"] != "NO CONVENCIONAL") & a["fecha"].isin(meses)]
        dif = (resto.groupby("fecha")[col_pozos].sum() - nacional.loc[meses, col_serie]).abs().max()
        composicion = resto.groupby("tipo_de_recurso")[col_pozos].sum().round(1).to_dict()
        anotar(f"Convencional de la serie ({producto}) = pozos que no son NO CONVENCIONAL en el archivo anual 2026",
               ok(dif < 0.5), f"{len(meses)} meses en que las dos versiones coinciden ({', '.join(meses.strftime('%m/%Y'))}); "
                              f"diferencia máxima {dif:.3f}; composición por tipo de recurso: {composicion}")

    # Total vs. suma de cuencas.
    cuencas_p = [c for c in petroleo.columns if c.startswith("cuenca_")]
    cuencas_g = [c for c in gas.columns if c.startswith("produccion_gas_natural_cuenca_")]
    dif_p = 100 * ((petroleo["total"] - petroleo[cuencas_p].sum(axis=1)) / petroleo["total"]).abs()
    dif_g = 100 * ((gas["produccion_gas_natural_total"] - gas[cuencas_g].sum(axis=1)) / gas["produccion_gas_natural_total"]).abs()
    meses = dif_p[dif_p > 1e-6].index
    anotar("Total = suma de las cinco cuencas", ok(max(dif_p.max(), dif_g.max()) < 0.01),
           f"petróleo: diferencia máxima {dif_p.max():.4f}% ({len(meses)} meses, {meses.min():%m/%Y} a {meses.max():%m/%Y}); "
           f"gas: {dif_g.max():.6f}%")

    # Archivo no convencional vs. serie agregada.
    for producto in ("petroleo", "gas"):
        for subtipo in ("shale", "tight"):
            d = comparacion[f"{producto}_{subtipo}_dif"]
            con_dif = d[d.abs() > 0.01]
            aclaracion = " (tight + pozos no convencionales sin subtipo)" if subtipo == "tight" else ""
            anotar(f"Archivo no convencional vs. serie agregada: {producto} {subtipo}{aclaracion}, {len(d)} meses",
                   "OK" if con_dif.empty else "DIFERENCIAS",
                   "coinciden todos los meses" if con_dif.empty else
                   "; ".join(f"{f:%Y-%m}: {v:,.1f}" for f, v in con_dif.items()))

    # Regla "no convencional sin subtipo = tight".
    for producto in ("petroleo", "gas"):
        meses = len(regla)
        cierra = {h: int((regla[f"{producto}_{c}"].abs() < 0.01).sum()) for h, c in
                  (("no se cuentan", "tight_dif_si_no_se_cuentan"), ("son tight", "tight_dif_si_son_tight"),
                   ("son shale", "shale_dif_si_son_shale"))}
        anotar(f"Regla 'no convencional sin subtipo = tight' ({producto}): meses con pozos sin subtipo en que cierra cada hipótesis",
               "EVIDENCIA", f"{meses} meses con pozos sin subtipo; cierra si no se cuentan: {cierra['no se cuentan']}, "
                            f"si son tight: {cierra['son tight']}, si son shale: {cierra['son shale']}")

    # Cobertura del archivo no convencional vs. archivos anuales completos.
    for anio, tabla in coberturas.items():
        huecos = tabla[tabla["pozo_mes_solo_en_anual"] > 0]
        anotar(f"Cobertura {anio}: pozo-mes NO CONVENCIONAL del archivo anual completo vs. archivo no convencional",
               "OK" if tabla[["pozo_mes_solo_en_anual", "pozo_mes_solo_en_no_convencional", "pozo_mes_con_petroleo_distinto"]].sum().sum() == 0
               else "DIFERENCIAS",
               f"en los dos {int(tabla['pozo_mes_en_los_dos'].sum())}, solo en el anual {int(tabla['pozo_mes_solo_en_anual'].sum())}, "
               f"solo en el no convencional {int(tabla['pozo_mes_solo_en_no_convencional'].sum())}, con petróleo distinto "
               f"{int(tabla['pozo_mes_con_petroleo_distinto'].sum())}"
               + (f"; huecos (meses con pozos que faltan en el no convencional): "
                  + ", ".join(f"{f:%Y-%m} ({int(r.pozo_mes_solo_en_anual)} pozos, {-r.dif_petroleo_m3:,.1f} m3 de petróleo)"
                              for f, r in huecos.iterrows()) if len(huecos) else ""))

    # Archivos anuales completos (todos los pozos) vs. serie agregada: total, shale y tight.
    for anio, tabla in anuales_vs.items():
        partes = []
        for c, nombre in (("petroleo_total", "petróleo total"), ("petroleo_shale", "petróleo shale"),
                          ("petroleo_tight", "petróleo tight"), ("gas_total", "gas total"), ("gas_shale", "gas shale")):
            con_dif = tabla[tabla[f"{c}_dif"].abs() > 0.5]  # la serie viene redondeada
            if len(con_dif):
                partes.append(f"{nombre}: " + ", ".join(f"{f:%Y-%m} {v:,.1f}" for f, v in con_dif[f"{c}_dif"].items()))
        anotar(f"Archivo anual completo {anio} (todos los pozos) vs. serie agregada, por mes (total, shale y tight)",
               "OK" if not partes else "DIFERENCIAS",
               f"{len(tabla)} meses; " + ("coinciden todos" if not partes else "; ".join(partes)))

    # Corte: ningún mes posterior al último mes completo de la fuente oficial.
    anotar("Ninguna serie tiene meses posteriores al último mes completo de la fuente oficial (último mes de la serie agregada)",
           ok(all(s.index.max() <= ultimo_mes_completo for s in series.values())),
           f"último mes completo {ultimo_mes_completo:%m/%Y}; " + ", ".join(f"{n} hasta {s.index.max():%m/%Y}" for n, s in series.items()))
    return pd.DataFrame(resultados)


def comparar_versiones_2026(petroleo, gas, anual_2026) -> pd.DataFrame:
    """Serie agregada (versión del portal al FECHA_SERIE_AGREGADA) vs. archivo anual por pozo de 2026
    (más reciente), por mes, y lo cargado después de la serie agregada según fechaingreso."""
    a = anual_2026.copy()
    a["cargado_despues"] = pd.to_datetime(a["fechaingreso"], errors="coerce") > pd.Timestamp(FECHA_SERIE_AGREGADA) + pd.Timedelta(days=1)
    por_mes = a.groupby("fecha").agg(petroleo_m3_anual=("prod_pet", "sum"), gas_miles_m3_anual=("prod_gas", "sum"),
                                     filas=("idpozo", "size"))
    tarde = a[a["cargado_despues"]].groupby("fecha").agg(filas_cargadas_despues=("idpozo", "size"),
                                                         petroleo_m3_cargado_despues=("prod_pet", "sum"),
                                                         gas_miles_m3_cargado_despues=("prod_gas", "sum"))
    tabla = por_mes.join(tarde).fillna(0)
    # Los meses posteriores al último de la serie agregada están incompletos en el archivo por pozo:
    # quedan en esta tabla solo como evidencia, nunca en una serie (ver verificar_corte).
    tabla.insert(0, "mes_completo_en_fuente_oficial", tabla.index <= petroleo.index.max())
    tabla["petroleo_m3_serie_agregada"] = petroleo["total"]
    tabla["gas_miles_m3_serie_agregada"] = gas["produccion_gas_natural_total"]
    tabla["dif_petroleo_m3"] = tabla["petroleo_m3_anual"] - tabla["petroleo_m3_serie_agregada"]
    tabla["dif_gas_miles_m3"] = tabla["gas_miles_m3_anual"] - tabla["gas_miles_m3_serie_agregada"]
    dias = pd.Series(tabla.index.days_in_month, index=tabla.index)
    tabla["petroleo_kbbl_d_anual"] = tabla["petroleo_m3_anual"] * BARRILES_POR_M3 / dias / 1000
    tabla["petroleo_kbbl_d_serie_agregada"] = tabla["petroleo_m3_serie_agregada"] * BARRILES_POR_M3 / dias / 1000
    tabla["gas_mm3_d_anual"] = tabla["gas_miles_m3_anual"] / dias / 1000
    tabla["gas_mm3_d_serie_agregada"] = tabla["gas_miles_m3_serie_agregada"] / dias / 1000
    tabla.index.name = "fecha"
    return tabla


def contrastar_primera_difusion(nacional, vaca_muerta, versiones, sesco) -> pd.DataFrame:
    """Primera difusión vs. dato vigente. No aprueba ni rechaza: muestra la revisión."""
    columna_vigente = {"petroleo_total": (nacional, "petroleo_total_kbbl_d"), "gas_total": (nacional, "gas_total_mm3_d"),
                       "petroleo_vaca_muerta": (vaca_muerta, "petroleo_kbbl_d")}
    columna_2026 = {"petroleo_total": "petroleo_kbbl_d_anual", "gas_total": "gas_mm3_d_anual"}
    filas = []
    for serie, mes, valor, unidad, fuente in PRIMERA_DIFUSION:
        fecha = pd.Timestamp(mes + "-01")
        tabla, columna = columna_vigente[serie]
        vigente = tabla.loc[fecha, columna]
        fila = {"serie": serie, "mes": mes, "unidad": unidad, "primera_difusion": valor, "fuente_primera_difusion": fuente,
                "dato_vigente": vigente, "revision_pct": 100 * (vigente / valor - 1),
                "dato_vigente_de": "serie agregada de la SE" if serie != "petroleo_vaca_muerta" else "archivo no convencional por pozo"}
        if serie in columna_2026 and fecha in versiones.index:
            fila["pozo_a_pozo_anual_2026"] = versiones.loc[fecha, columna_2026[serie]]
            fila["revision_pct_pozo_a_pozo"] = 100 * (fila["pozo_a_pozo_anual_2026"] / valor - 1)
        dias = fecha.days_in_month
        if serie == "petroleo_total" and fecha in sesco.index and pd.notna(sesco.loc[fecha, "petroleo_produccion_petroleo_promedio_dia_m3"]):
            fila["sesco"] = sesco.loc[fecha, "petroleo_produccion_petroleo_promedio_dia_m3"] * BARRILES_POR_M3 / 1000
        if serie == "gas_total" and fecha in sesco.index:
            fila["sesco"] = sesco.loc[fecha, "gas_produccion_gas_promedio_dia_mm3"] / 1000
        if "sesco" in fila:
            fila["revision_pct_sesco"] = 100 * (fila["sesco"] / valor - 1)
        filas.append(fila)
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------------------------
def main():
    sys.stdout.reconfigure(encoding="utf-8")
    VALIDACION.mkdir(parents=True, exist_ok=True)

    print("Series agregadas de la SE...")
    agregadas, registros = se.descargar_series_agregadas()
    petroleo, gas = agregadas["petroleo"], agregadas["gas"]
    print("Producción por pozo: no convencionales y anuales para controles...")
    pozos_nc, registro = se.descargar_pozos_no_convencional()
    registros.append(registro)
    anuales = {}
    for anio in ANIOS_COBERTURA:
        anuales[anio], registro = se.descargar_pozos_anual(anio)
        registros.append(registro)
    anual_2026 = anuales[2026]
    print("SESCO (solo para controles)...")
    sesco, regs = se.descargar_sesco_diaria()
    registros += regs

    # Último mes completo de la fuente oficial: el último mes de la serie agregada de la SE.
    ultimo_mes_completo = min(petroleo.index.max(), gas.index.max())

    nacional = armar_nacional(petroleo, gas)
    comparacion = comparar_no_convencional_con_serie(pozos_nc[pozos_nc["fecha"] <= ultimo_mes_completo], petroleo, gas)
    regla = evidencia_regla_sin_subtipo(comparacion)
    no_cierran = meses_que_no_cierran(comparacion)
    coberturas = {anio: cobertura(pozos_nc, anual, anio, ultimo_mes_completo) for anio, anual in anuales.items()}
    anuales_vs = {anio: anual_vs_serie(anual, petroleo, gas, anio, ultimo_mes_completo) for anio, anual in anuales.items()}
    vaca_muerta = armar_vaca_muerta(pozos_nc, comparacion, ultimo_mes_completo)
    series = {"produccion_petroleo_gas_mensual": nacional, "produccion_vaca_muerta_mensual": vaca_muerta}
    verificar_corte(series, ultimo_mes_completo)  # si una serie se pasa del último mes completo, frena acá
    versiones = comparar_versiones_2026(petroleo, gas, anual_2026)
    tabla_controles = controles(petroleo, gas, nacional, comparacion, regla, coberturas, anuales_vs, anual_2026,
                                series, ultimo_mes_completo)
    difusion = contrastar_primera_difusion(nacional, vaca_muerta, versiones, sesco)

    nacional.to_csv(PROCESADOS / "produccion_petroleo_gas_mensual.csv", float_format="%.4f", date_format="%Y-%m-%d")
    vaca_muerta.to_csv(PROCESADOS / "produccion_vaca_muerta_mensual.csv", float_format="%.4f", date_format="%Y-%m-%d")
    tabla_controles.to_csv(VALIDACION / "produccion_controles.csv", index=False)
    comparacion.to_csv(VALIDACION / "produccion_no_convencional_vs_serie.csv", float_format="%.3f", date_format="%Y-%m-%d")
    regla.to_csv(VALIDACION / "produccion_regla_sin_subtipo.csv", float_format="%.3f", date_format="%Y-%m-%d")
    no_cierran.to_csv(VALIDACION / "produccion_meses_que_no_cierran.csv", index=False, float_format="%.4f", date_format="%Y-%m-%d")
    pd.concat(coberturas.values()).to_csv(VALIDACION / "produccion_cobertura_no_convencional.csv", float_format="%.3f", date_format="%Y-%m-%d")
    pd.concat(anuales_vs.values()).to_csv(VALIDACION / "produccion_anuales_vs_serie.csv", float_format="%.3f", date_format="%Y-%m-%d")
    versiones.to_csv(VALIDACION / "produccion_versiones_2026.csv", float_format="%.3f", date_format="%Y-%m-%d")
    difusion.to_csv(VALIDACION / "produccion_vs_primera_difusion.csv", index=False, float_format="%.3f")
    guardar_registro(registros, VALIDACION / "descargas_produccion.csv")

    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 140)
    print(f"\nNacional: {nacional.index.min():%m/%Y} a {nacional.index.max():%m/%Y}. "
          f"Vaca Muerta: {vaca_muerta.index.min():%m/%Y} a {vaca_muerta.index.max():%m/%Y}")
    print("\nControles:\n" + tabla_controles.to_string(index=False))
    print("\nMeses en que el archivo no convencional no reproduce la serie:\n"
          + no_cierran.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    for anio, tabla in coberturas.items():
        con_dif = tabla[(tabla[["pozo_mes_solo_en_anual", "pozo_mes_solo_en_no_convencional", "pozo_mes_con_petroleo_distinto"]] > 0).any(axis=1)]
        print(f"\nCobertura {anio}, meses con diferencias:\n" + (con_dif.round(1).to_string() if len(con_dif) else "ninguno"))
    print("\nPrimera difusión vs. dato vigente:\n" + difusion.drop(columns=["fuente_primera_difusion", "dato_vigente_de"]).round(2).to_string(index=False))
    print("\nVersiones 2026 (serie agregada vs. archivo anual):\n" + versiones[
        ["petroleo_kbbl_d_serie_agregada", "petroleo_kbbl_d_anual", "gas_mm3_d_serie_agregada", "gas_mm3_d_anual",
         "filas_cargadas_despues", "petroleo_m3_cargado_despues"]].round(2).to_string())


if __name__ == "__main__":
    main()
