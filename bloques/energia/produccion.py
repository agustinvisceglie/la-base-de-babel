"""
Bloque 2, energía: producción de petróleo y gas de la Argentina (armador; migrado en el Paso 3c
desde series/produccion_hidrocarburos.py).

Qué hace:
    1. Serie mensual nacional de petróleo y gas por subtipo de recurso (convencional, shale y tight)
       con las series agregadas oficiales de la Secretaría de Energía (SE) "por cuenca y sub tipo de
       recurso (Capítulo IV)", desde enero de 2006 hasta el último mes publicado.
       - Convencional = total - shale - tight. Para la SE, no convencional = shale + tight: su columna
         de participación no convencional es (shale + tight) / total (control "no convencional").
    2. Serie mensual de Vaca Muerta desde enero de 2010 (criterios, sección 3, y Paso 1 del instructivo):
       - volúmenes por pozo de la variante "DDJJ abiertas y cerradas" de cada año (2010-2026);
       - clasificación de cada pozo (tipo de recurso, subtipo y formación) tomada de la publicación
         más reciente de la SE que lo contiene, entre los DDJJ de cada año y el archivo de pozos no
         convencionales, en todas sus versiones guardadas (regla general, no un parche por pozo);
       - Vaca Muerta = formación productiva (formprod) VMUT y tipo de recurso NO CONVENCIONAL.
    3. Controles (en datos/validacion/energia/):
       - internos de las series agregadas (meses, vacíos, unidades, factor, subtipos, cuencas);
       - DDJJ con la clasificación vigente vs. serie agregada, mes por mes desde 2010: total, shale y
         tight, petróleo y gas (tight = TIGHT + no convencional sin subtipo, regla de la SE), y lo que
         daría la clasificación propia de cada archivo;
       - reclasificaciones: todo pozo cuya clasificación difiere entre publicaciones o versiones, con
         el volumen que cambia de agregado al aplicar la regla;
       - Vaca Muerta con los DDJJ vs. Vaca Muerta con el archivo no convencional (método anterior);
       - archivo no convencional vs. serie agregada (shale y tight) y evidencia de la regla "no
         convencional sin subtipo = tight";
       - cobertura del archivo no convencional vs. archivos anuales completos (ANIOS_COBERTURA), y
         esos anuales vs. la serie agregada (total, shale y tight);
       - corte: ninguna serie puede tener meses posteriores al último mes completo de la fuente
         oficial (el último mes de la serie agregada); si pasa, el script se detiene;
       - versiones: serie agregada vs. archivo anual de 2026 (más reciente), por mes;
       - primera difusión vs. dato vigente (sin aprobar ni rechazar: se muestra la revisión).
    Antes de bajar nada revisa el portal: si no responde, o si lo que cambió supera 1 GB y no se pasó
    actualizar.py --ok-descarga-grande, frena sin bajar (regla 8 del instructivo). Con
    --sin-descargar o --crudos-al no usa internet: lee las versiones registradas.
    Cada crudo se guarda como versión comprimida (fecha de publicación + hash) en
    datos/crudos/secretaria_energia/versiones/; el registro queda en datos/registros/versiones_crudos.csv.

Unidades:
    - petróleo: m3 del mes, m3/d (m3 ÷ días del mes) y kbbl/d (m3 × 6,28981 ÷ días del mes ÷ 1.000);
    - gas: miles de m3 del mes y MMm3/d (miles de m3 ÷ días del mes ÷ 1.000).

Decisiones pendientes (no se toman acá): promedio anual; corte común de cada nota.

Fuentes: SE, datos.energia.gob.ar (lector: lectores/secretaria_energia.py).

Genera (lo escribe actualizar.py):
    - datos/series/energia/produccion_petroleo_gas_mensual.csv y produccion_vaca_muerta_mensual.csv
    - datos/validacion/energia/produccion_controles.csv y las tablas de validación produccion_*.csv
      (ddjj_vs_serie, reclasificaciones, vaca_muerta_ddjj_vs_no_convencional, no_convencional_vs_serie,
      regla_sin_subtipo, meses_que_no_cierran, cobertura_no_convencional, anuales_vs_serie,
      versiones_2026, vs_primera_difusion) y descargas_produccion.csv

Uso (desde la raíz del repositorio):
    .venv/Scripts/python actualizar.py --bloque energia [--ok-descarga-grande]
"""

import numpy as np
import pandas as pd

from comun import descargas
from lectores import secretaria_energia as se

BARRILES_POR_M3 = 6.28981  # el mismo factor que usa la SE en su columna kbbl_diario (ver controles)
SUBTIPOS = ["total", "convencional", "shale", "tight"]
DESDE_VACA_MUERTA = "2010-01-01"
# Tolerancia para decir que una suma por pozo "cierra" contra la serie agregada: la serie viene
# redondeada (la misma que se usó en eb152d9). Las diferencias se informan siempre, cierren o no.
TOLERANCIA_SERIE = 0.5
# Años en que se contrastan los archivos anuales completos (todos los pozos) contra el archivo no
# convencional y contra la serie agregada. 2015: uno de 2010-2015, con un mes que no cierra (06/2015);
# 2024: el año del hueco de 09/2024; 2026: el más reciente.
ANIOS_COBERTURA = [2015, 2024, 2026]

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
# Declaración de series (de acá sale el catálogo)
# ---------------------------------------------------------------------------------------------
_URL_SERIES = "http://datos.energia.gob.ar/dataset/c846e79c-026c-4040-897f-1ad3543b407c"
_ID_PETROLEO = "c846e79c-026c-4040-897f-1ad3543b407c / af8c50bb-fde0-43b7-98eb-7cd14daf586c (serie de petróleo por cuenca y sub tipo de recurso)"
_ID_GAS = "c846e79c-026c-4040-897f-1ad3543b407c / a3244ddd-38bc-4800-a700-360b649d2f3a (serie de gas natural por cuenca y sub tipo de recurso)"
_ID_POZOS = ("c846e79c-026c-4040-897f-1ad3543b407c: producción por pozo, variante DDJJ abiertas y cerradas 2010-2026, y "
             "archivo de pozos no convencionales (clasificación de la publicación más reciente)")
_UNIDADES = {"m3_mes": "m3 del mes", "m3_d": "m3 por día", "kbbl_d": "miles de barriles por día",
             "miles_m3_mes": "miles de m3 del mes", "mm3_d": "millones de m3 por día", "pozos": "pozos con registro en el mes"}
_NOMBRES = {"total": "total del país", "convencional": "convencional", "shale": "shale", "tight": "tight"}
_CRITERIO = "§3 Producción de petróleo y gas (serie oficial agregada de la SE)"
_CRITERIO_VM = "§3 Producción: Vaca Muerta = VMUT + no convencional, DDJJ abiertas y cerradas con la clasificación más reciente"


def _serie(archivo, columna, nombre, unidad, fuente_id, criterio):
    return {"archivo": archivo, "columna": columna, "nombre": nombre, "unidad": unidad, "frecuencia": "mensual",
            "tipo": "nivel", "precios": "no aplica", "ajuste_estacional": "original", "uso": "base",
            "organismo": "Secretaría de Energía", "rotulo": "oficial", "fuente_id": fuente_id, "fuente_url": _URL_SERIES,
            "lector": "lectores/secretaria_energia.py", "criterio": criterio, "estimados": "no",
            "tiene_revisiones": "sí: la SE revisa los meses recientes; la base usa el dato vigente (ver la validación)",
            "discontinuada": "no", "con_reservas": "no", "informe_validacion": "datos/validacion/energia/produccion_informe_validacion.md"}


SERIES = (
    [_serie("produccion_petroleo_gas_mensual.csv", f"petroleo_{s}_{u}", f"Producción de petróleo, {_NOMBRES[s]}", _UNIDADES[u], _ID_PETROLEO, _CRITERIO)
     for u in ("m3_mes", "m3_d", "kbbl_d") for s in SUBTIPOS]
    + [_serie("produccion_petroleo_gas_mensual.csv", f"gas_{s}_{u}", f"Producción de gas natural, {_NOMBRES[s]}", _UNIDADES[u], _ID_GAS, _CRITERIO)
       for u in ("miles_m3_mes", "mm3_d") for s in SUBTIPOS]
    + [_serie("produccion_vaca_muerta_mensual.csv", columna, nombre, _UNIDADES[u], _ID_POZOS, _CRITERIO_VM)
       for columna, nombre, u in (("petroleo_m3_mes", "Producción de petróleo de Vaca Muerta", "m3_mes"),
                                  ("petroleo_m3_d", "Producción de petróleo de Vaca Muerta", "m3_d"),
                                  ("petroleo_kbbl_d", "Producción de petróleo de Vaca Muerta", "kbbl_d"),
                                  ("gas_miles_m3_mes", "Producción de gas natural de Vaca Muerta", "miles_m3_mes"),
                                  ("gas_mm3_d", "Producción de gas natural de Vaca Muerta", "mm3_d"),
                                  ("pozos_con_registro", "Pozos de Vaca Muerta con registro en el mes", "pozos"))]
)
AUXILIARES = {"produccion_petroleo_gas_mensual.csv": ["dias_del_mes"],
              "produccion_vaca_muerta_mensual.csv": ["dias_del_mes", "control_shale_vs_serie"]}
FORMATO = {"produccion_petroleo_gas_mensual.csv": "%.4f", "produccion_vaca_muerta_mensual.csv": "%.4f"}


# ---------------------------------------------------------------------------------------------
# 1. Serie nacional (serie agregada de la SE)
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


# ---------------------------------------------------------------------------------------------
# 2. Datos por pozo: variante "DDJJ abiertas y cerradas" con la clasificación más reciente
# ---------------------------------------------------------------------------------------------
def clave_clasificacion(tabla: pd.DataFrame) -> pd.Series:
    """Clasificación de cada fila como texto "tipo de recurso|subtipo|formación" (vacío si falta)."""
    tipo, subtipo, formacion = (tabla[c].astype("string").fillna("") for c in ("tipo_de_recurso", "sub_tipo_recurso", "formprod"))
    return tipo + "|" + subtipo + "|" + formacion


def atributos_claves(claves) -> pd.DataFrame:
    """Para cada clave de clasificación: tipo, subtipo, formación y a qué agregado va. Reglas de la
    SE: no convencional = shale + tight; un pozo no convencional sin subtipo cuenta como tight
    (evidencia en produccion_regla_sin_subtipo.csv); Vaca Muerta = formación VMUT y no convencional."""
    tabla = pd.Series(sorted(set(claves)), dtype="string").str.split("|", expand=True)
    tabla.columns = ["tipo_de_recurso", "sub_tipo_recurso", "formprod"]
    tabla.index = tabla["tipo_de_recurso"] + "|" + tabla["sub_tipo_recurso"] + "|" + tabla["formprod"]
    tabla.index.name = "clave"
    no_convencional = tabla["tipo_de_recurso"] == "NO CONVENCIONAL"
    tabla["shale"] = no_convencional & (tabla["sub_tipo_recurso"] == "SHALE")
    tabla["tight"] = no_convencional & (tabla["sub_tipo_recurso"] != "SHALE")
    tabla["vaca_muerta"] = no_convencional & (tabla["formprod"] == "VMUT")
    return tabla


def compactar_publicacion(tabla: pd.DataFrame) -> pd.DataFrame:
    """Una publicación por pozo reducida a lo que se usa: pozo, mes, volúmenes, clave de clasificación,
    campo (areayacimiento) y cuenca."""
    return pd.DataFrame({"idpozo": tabla["idpozo"].to_numpy(), "anio": tabla["anio"].to_numpy(),
                         "fecha": tabla["fecha"].to_numpy(), "prod_pet": tabla["prod_pet"].to_numpy(),
                         "prod_gas": tabla["prod_gas"].to_numpy(),
                         "clave": clave_clasificacion(tabla).astype("category").array,
                         "campo": tabla["areayacimiento"].astype("category").array,
                         "cuenca": tabla["cuenca"].astype("category").array})


def clasificacion_por_publicacion(nombre: str, compacta: pd.DataFrame, fecha_publicacion: str) -> pd.DataFrame:
    """Una fila por pozo de una publicación: su clasificación (la de su último mes en ese archivo),
    campo y cuenca, y cuántas clasificaciones distintas tiene dentro de esa misma publicación."""
    distintas = compacta.groupby("idpozo", observed=True)["clave"].nunique()
    ultima = compacta.sort_values("fecha", kind="stable").groupby("idpozo", observed=True).tail(1).set_index("idpozo")
    resultado = pd.DataFrame({"clave": ultima["clave"].astype("string"), "campo": ultima["campo"].astype("string"),
                              "cuenca": ultima["cuenca"].astype("string")})
    resultado["clasificaciones_en_la_publicacion"] = distintas.reindex(resultado.index)
    resultado["publicacion"] = nombre
    resultado["fecha_publicacion"] = fecha_publicacion
    return resultado.reset_index()


def clasificacion_vigente(por_publicacion: pd.DataFrame) -> pd.DataFrame:
    """Clasificación de cada pozo según la publicación más reciente de la SE que lo contiene
    (criterios, sección 3: regla general, no un parche por pozo). Índice: idpozo."""
    return (por_publicacion.sort_values(["fecha_publicacion", "publicacion"], kind="stable")
            .groupby("idpozo").tail(1).set_index("idpozo"))


def sumas_mensuales(volumenes: pd.DataFrame, claves: pd.Series, atributos: pd.DataFrame) -> pd.DataFrame:
    """Suma mensual de los volúmenes por pozo: total, shale, tight y Vaca Muerta (petróleo y gas),
    con la clave de clasificación indicada para cada fila (`claves`, en el mismo orden que
    `volumenes`), y pozos de Vaca Muerta con registro."""
    claves = pd.Series(claves).astype("category")
    codigos = claves.cat.codes.to_numpy()
    posiciones = atributos.index.get_indexer(pd.Index(claves.cat.categories.astype(object)))
    if len(codigos) != len(volumenes) or (codigos < 0).any() or (posiciones < 0).any():
        raise ValueError("Hay pozo-mes sin clasificación: no se puede sumar")
    fila = posiciones[codigos]
    pet, gas = volumenes["prod_pet"].to_numpy(), volumenes["prod_gas"].to_numpy()
    tabla = pd.DataFrame({"fecha": volumenes["fecha"].to_numpy(), "petroleo_total": pet, "gas_total": gas})
    for agregado in ("shale", "tight", "vaca_muerta"):
        marca = atributos[agregado].to_numpy(dtype=bool)[fila]
        tabla[f"petroleo_{agregado}"] = np.where(marca, pet, 0.0)
        tabla[f"gas_{agregado}"] = np.where(marca, gas, 0.0)
    tabla["pozos_vaca_muerta"] = atributos["vaca_muerta"].to_numpy(dtype=int)[fila]
    return tabla.groupby("fecha").sum()


def ddjj_vs_serie(vigentes: pd.DataFrame, propias: pd.DataFrame, petroleo: pd.DataFrame, gas: pd.DataFrame) -> pd.DataFrame:
    """Verificación mes por mes: DDJJ con la clasificación vigente vs. serie agregada de la SE (total,
    shale y tight, petróleo y gas), y la diferencia que daría la clasificación propia de cada archivo."""
    series = {"petroleo": {"total": petroleo["total"], "shale": petroleo["shale"], "tight": petroleo["tight"]},
              "gas": {"total": gas["produccion_gas_natural_total"], "shale": gas["produccion_shale_gas"],
                      "tight": gas["produccion_tight_gas"]}}
    meses = vigentes.index.intersection(petroleo.index).intersection(gas.index)
    tabla = pd.DataFrame(index=meses)
    for producto, por_agregado in series.items():
        for agregado, serie in por_agregado.items():
            tabla[f"{producto}_{agregado}_ddjj"] = vigentes.loc[meses, f"{producto}_{agregado}"]
            tabla[f"{producto}_{agregado}_serie"] = serie.loc[meses]
            tabla[f"{producto}_{agregado}_dif"] = tabla[f"{producto}_{agregado}_ddjj"] - tabla[f"{producto}_{agregado}_serie"]
        for agregado in ("shale", "tight"):
            tabla[f"{producto}_{agregado}_dif_clasificacion_propia"] = (propias.loc[meses, f"{producto}_{agregado}"]
                                                                        - por_agregado[agregado].loc[meses])
    dias = pd.Series(meses.days_in_month, index=meses)
    tabla["petroleo_total_dif_kbbl_d"] = tabla["petroleo_total_dif"] * BARRILES_POR_M3 / dias / 1000
    tabla["petroleo_total_dif_pct"] = 100 * tabla["petroleo_total_dif"] / tabla["petroleo_total_serie"]
    tabla["gas_total_dif_pct"] = 100 * tabla["gas_total_dif"] / tabla["gas_total_serie"]
    columnas_dif = [f"{p}_{a}_dif" for p in ("petroleo", "gas") for a in ("total", "shale", "tight")]
    tabla["cierra"] = (tabla[columnas_dif].abs() <= TOLERANCIA_SERIE).all(axis=1)
    tabla.index.name = "fecha"
    return tabla


def _describir(clave: str) -> str:
    tipo, subtipo, formacion = clave.split("|")
    return f"{tipo or '(sin tipo)'} / {subtipo or '(sin subtipo)'} / {formacion or '(sin formación)'}"


def _nombre_publicacion(nombre: str, fecha_publicacion: str) -> str:
    return f"{nombre} (publicado el {pd.Timestamp(fecha_publicacion):%d/%m/%Y})"


def reclasificaciones(por_publicacion: pd.DataFrame, vigente: pd.DataFrame, publicaciones: dict, volumenes: pd.DataFrame,
                      atributos: pd.DataFrame) -> pd.DataFrame:
    """Pozos cuya clasificación difiere entre publicaciones o versiones de la SE. Una fila por pozo y por
    clasificación distinta de la vigente, con campo y cuenca, la publicación más vieja y la más nueva que
    tienen esa clasificación, la publicación vigente y su clasificación, y los pozo-mes de los DDJJ que
    cambian de clasificación al aplicar la regla (con su volumen).

    Control de la regla: cuántos de esos pozo-mes tendrían otra clasificación si la regla se aplicara
    por pozo-mes (la publicación más reciente que contiene ese mes) en lugar de por pozo."""
    distintas = por_publicacion.groupby("idpozo")["clave"].nunique()
    pozos = distintas[distintas > 1].index
    columnas = ["idpozo", "campo", "cuenca", "clasificacion_anterior", "primera_publicacion_con_la_anterior",
                "ultima_publicacion_con_la_anterior", "publicaciones_con_la_anterior", "clasificacion_vigente",
                "publicacion_vigente", "que_cambia", "cambia_vaca_muerta", "pozo_mes_ddjj_que_cambian", "desde", "hasta",
                "petroleo_m3_que_cambia", "gas_miles_m3_que_cambia", "pozo_mes_distintos_si_la_regla_fuera_por_pozo_mes"]
    if len(pozos) == 0:
        return pd.DataFrame(columns=columnas)

    # Regla por pozo-mes, solo para estos pozos: la publicación más reciente que contiene cada pozo-mes.
    presencia = pd.concat([c.loc[c["idpozo"].isin(pozos), ["idpozo", "fecha", "clave"]].assign(
        clave=lambda x: x["clave"].astype("string"), fecha_publicacion=fecha)
        for c, fecha in publicaciones.values()])
    por_pozo_mes = presencia.sort_values("fecha_publicacion").groupby(["idpozo", "fecha"]).tail(1).set_index(["idpozo", "fecha"])["clave"]
    propios = volumenes[volumenes["idpozo"].isin(pozos)].assign(clave=lambda x: x["clave"].astype("string"))

    filas = []
    for pozo in pozos:
        vig = vigente.loc[pozo]
        del_pozo = por_publicacion[por_publicacion["idpozo"] == pozo].sort_values("fecha_publicacion")
        propios_pozo = propios[propios["idpozo"] == pozo]
        alternativa = por_pozo_mes.reindex(pd.MultiIndex.from_arrays([propios_pozo["idpozo"], propios_pozo["fecha"]])).to_numpy()
        for clave, grupo in del_pozo[del_pozo["clave"] != vig["clave"]].groupby("clave", sort=False):
            cambian = propios_pozo[propios_pozo["clave"] == clave]
            ant, nueva = atributos.loc[clave], atributos.loc[vig["clave"]]
            filas.append({
                "idpozo": pozo, "campo": vig["campo"], "cuenca": vig["cuenca"],
                "clasificacion_anterior": _describir(clave),
                "primera_publicacion_con_la_anterior": _nombre_publicacion(grupo["publicacion"].iloc[0], grupo["fecha_publicacion"].iloc[0]),
                "ultima_publicacion_con_la_anterior": _nombre_publicacion(grupo["publicacion"].iloc[-1], grupo["fecha_publicacion"].iloc[-1]),
                "publicaciones_con_la_anterior": len(grupo),
                "clasificacion_vigente": _describir(vig["clave"]),
                "publicacion_vigente": _nombre_publicacion(vig["publicacion"], vig["fecha_publicacion"]),
                "que_cambia": ("tipo de recurso o subtipo" if (ant["tipo_de_recurso"], ant["sub_tipo_recurso"])
                               != (nueva["tipo_de_recurso"], nueva["sub_tipo_recurso"]) else "solo la formación"),
                "cambia_vaca_muerta": bool(ant["vaca_muerta"] != nueva["vaca_muerta"]),
                "pozo_mes_ddjj_que_cambian": len(cambian),
                "desde": cambian["fecha"].min(), "hasta": cambian["fecha"].max(),
                "petroleo_m3_que_cambia": cambian["prod_pet"].sum(), "gas_miles_m3_que_cambia": cambian["prod_gas"].sum(),
                "pozo_mes_distintos_si_la_regla_fuera_por_pozo_mes": int((alternativa != vig["clave"]).sum()),
            })
    return pd.DataFrame(filas, columns=columnas)


def armar_vaca_muerta(vigentes: pd.DataFrame, verificacion: pd.DataFrame, ultimo_mes_completo: pd.Timestamp) -> pd.DataFrame:
    """Vaca Muerta (formación VMUT y no convencional, clasificación vigente) desde enero de 2010 hasta el
    último mes completo de la fuente oficial. La columna control marca los meses en que los DDJJ no
    reproducen el shale de la serie agregada (petróleo o gas)."""
    serie = vigentes.loc[(vigentes.index >= DESDE_VACA_MUERTA) & (vigentes.index <= ultimo_mes_completo),
                         ["petroleo_vaca_muerta", "gas_vaca_muerta", "pozos_vaca_muerta"]]
    serie = serie.reindex(pd.date_range(DESDE_VACA_MUERTA, serie.index.max(), freq="MS"))
    serie.columns = ["petroleo_m3_mes", "gas_miles_m3_mes", "pozos_con_registro"]
    serie.index.name = "fecha"
    dias = pd.Series(serie.index.days_in_month, index=serie.index)
    serie.insert(0, "dias_del_mes", dias)
    serie["petroleo_m3_d"] = serie["petroleo_m3_mes"] / dias
    serie["petroleo_kbbl_d"] = serie["petroleo_m3_mes"] * BARRILES_POR_M3 / dias / 1000
    serie["gas_mm3_d"] = serie["gas_miles_m3_mes"] / dias / 1000
    control = verificacion.reindex(serie.index)
    serie["control_shale_vs_serie"] = [
        "OK" if abs(p) <= TOLERANCIA_SERIE and abs(g) <= TOLERANCIA_SERIE else
        f"REVISAR: el shale de los DDJJ difiere de la serie agregada en {p:,.1f} m3 de petróleo y {g:,.1f} miles de m3 de gas"
        for p, g in zip(control["petroleo_shale_dif"], control["gas_shale_dif"])]
    columnas = ["dias_del_mes", "petroleo_m3_mes", "petroleo_m3_d", "petroleo_kbbl_d", "gas_miles_m3_mes",
                "gas_mm3_d", "pozos_con_registro", "control_shale_vs_serie"]
    return serie[columnas]


def vaca_muerta_vs_no_convencional(vaca_muerta: pd.DataFrame, pozos_nc: pd.DataFrame) -> pd.DataFrame:
    """Vaca Muerta con los DDJJ (método vigente) vs. con el archivo de pozos no convencionales (método
    anterior, solo DDJJ cerradas), por mes."""
    vm = pozos_nc[(pozos_nc["formprod"] == "VMUT") & (pozos_nc["tipo_de_recurso"] == "NO CONVENCIONAL")]
    anterior = vm.groupby("fecha").agg(petroleo_m3_no_convencional=("prod_pet", "sum"),
                                       gas_miles_m3_no_convencional=("prod_gas", "sum"),
                                       pozos_no_convencional=("idpozo", "nunique"))
    tabla = vaca_muerta[["petroleo_m3_mes", "gas_miles_m3_mes", "pozos_con_registro"]].join(anterior)
    tabla["dif_petroleo_m3"] = tabla["petroleo_m3_mes"] - tabla["petroleo_m3_no_convencional"]
    tabla["dif_gas_miles_m3"] = tabla["gas_miles_m3_mes"] - tabla["gas_miles_m3_no_convencional"]
    tabla["dif_pozos"] = tabla["pozos_con_registro"] - tabla["pozos_no_convencional"]
    dias = pd.Series(tabla.index.days_in_month, index=tabla.index)
    tabla["dif_petroleo_kbbl_d"] = tabla["dif_petroleo_m3"] * BARRILES_POR_M3 / dias / 1000
    return tabla


# ---------------------------------------------------------------------------------------------
# 3. Archivo de pozos no convencionales y anuales completos (controles)
# ---------------------------------------------------------------------------------------------
def comparar_no_convencional_con_serie(pozos_nc: pd.DataFrame, petroleo: pd.DataFrame, gas: pd.DataFrame) -> pd.DataFrame:
    """Suma mensual del archivo no convencional por subtipo vs. la serie agregada, todos los meses.
    La SE cuenta como tight a los pozos no convencionales sin subtipo: se muestran las dos sumas."""
    sub = pozos_nc["sub_tipo_recurso"].astype("string").fillna("SIN_SUBTIPO")
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
    por pozo pueden traer además meses parciales."""
    for nombre, serie in series.items():
        if serie.index.max() > ultimo_mes_completo:
            raise ValueError(f"{nombre} llega a {serie.index.max():%m/%Y}, después del último mes completo de la "
                             f"fuente oficial ({ultimo_mes_completo:%m/%Y})")


def cobertura(pozos_nc: pd.DataFrame, anual: pd.DataFrame, anio: int, ultimo_mes_completo: pd.Timestamp) -> pd.DataFrame:
    """Cobertura del archivo no convencional vs. un archivo anual completo, por mes y solo hasta el
    último mes completo de la fuente oficial: pozo-mes NO CONVENCIONAL que están en uno y no en el
    otro (huecos) y volúmenes distintos (revisiones)."""
    columnas = ["idpozo", "fecha", "prod_pet", "prod_gas"]
    anual_nc = anual.loc[(anual["tipo_de_recurso"] == "NO CONVENCIONAL") & (anual["fecha"] <= ultimo_mes_completo), columnas]
    nc = pozos_nc.loc[(pozos_nc["anio"] == anio) & (pozos_nc["fecha"] <= ultimo_mes_completo), columnas]
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


# ---------------------------------------------------------------------------------------------
# 4. Controles
# ---------------------------------------------------------------------------------------------
def controles(petroleo, gas, nacional, comparacion, regla, coberturas, anuales_vs, anual_2026, series, ultimo_mes_completo,
              verificacion, por_publicacion, reclasificados, vm_vs_nc, ddjj_resumen) -> pd.DataFrame:
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
    iguales = (a.groupby("fecha")["prod_pet"].sum() - petroleo["total"]).dropna().abs() < TOLERANCIA_SERIE
    meses = iguales[iguales].index
    for producto, col_pozos, col_serie in (("petróleo", "prod_pet", "petroleo_convencional_m3_mes"),
                                           ("gas", "prod_gas", "gas_convencional_miles_m3_mes")):
        resto = a[(a["tipo_de_recurso"] != "NO CONVENCIONAL") & a["fecha"].isin(meses)]
        dif = (resto.groupby("fecha")[col_pozos].sum() - nacional.loc[meses, col_serie]).abs().max()
        composicion = resto.groupby("tipo_de_recurso", observed=True)[col_pozos].sum().round(1).to_dict()
        anotar(f"Convencional de la serie ({producto}) = pozos que no son NO CONVENCIONAL en el archivo anual 2026",
               ok(dif < TOLERANCIA_SERIE), f"{len(meses)} meses en que las dos versiones coinciden ({', '.join(meses.strftime('%m/%Y'))}); "
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

    # Datos por pozo: DDJJ abiertas y cerradas con la clasificación vigente.
    anotar("DDJJ abiertas y cerradas: sin pozo-mes repetidos (dentro de cada archivo y entre archivos)",
           ok(ddjj_resumen["repetidos"] == 0),
           f"{ddjj_resumen['pozo_mes']:,} pozo-mes de {ddjj_resumen['anios']}; repetidos {ddjj_resumen['repetidos']}; "
           f"filas de otro año dentro de un DDJJ anual: {ddjj_resumen['filas_de_otro_anio']}")
    multiples = por_publicacion[por_publicacion["clasificaciones_en_la_publicacion"] > 1]
    anotar("Cada pozo tiene una sola clasificación dentro de cada publicación (la regla es por pozo)",
           ok(multiples.empty), f"{por_publicacion['publicacion'].nunique()} publicaciones y versiones; "
                                f"pozos con más de una clasificación en la misma publicación: {len(multiples)}")
    fechas = por_publicacion.drop_duplicates("publicacion")["fecha_publicacion"]
    anotar("Las publicaciones tienen fechas de publicación distintas (no hay empates para la regla)",
           ok(not fechas.duplicated().any()), f"{len(fechas)} publicaciones")
    for producto in ("petroleo", "gas"):
        for agregado in ("total", "shale", "tight"):
            d = verificacion[f"{producto}_{agregado}_dif"]
            fuera = d[d.abs() > TOLERANCIA_SERIE]
            anotar(f"DDJJ (clasificación vigente) vs. serie agregada: {producto} {agregado}, {len(d)} meses "
                   f"({d.index.min():%m/%Y} a {d.index.max():%m/%Y})",
                   "OK" if fuera.empty else "DIFERENCIAS",
                   f"diferencia máxima {d.abs().max():.3f}" + ("" if fuera.empty else
                   "; meses que no cierran: " + "; ".join(f"{f:%Y-%m}: {v:,.1f}" for f, v in fuera.items())))
        for agregado in ("shale", "tight"):
            d = verificacion[f"{producto}_{agregado}_dif_clasificacion_propia"]
            fuera = d[d.abs() > TOLERANCIA_SERIE]
            anotar(f"Evidencia: DDJJ con la clasificación propia de cada archivo vs. serie agregada: {producto} {agregado}",
                   "EVIDENCIA", f"meses que no cierran: {len(fuera)}" + ("" if fuera.empty else
                   " (" + "; ".join(f"{f:%Y-%m}: {v:,.1f}" for f, v in fuera.items()) + ")"))
    anotar("Reclasificaciones entre publicaciones o versiones (lista en produccion_reclasificaciones.csv)", "EVIDENCIA",
           f"{reclasificados['idpozo'].nunique()} pozos; cambian tipo o subtipo: "
           f"{int((reclasificados['que_cambia'] != 'solo la formación').sum())}; cambian Vaca Muerta: "
           f"{int(reclasificados['cambia_vaca_muerta'].sum())}; pozo-mes de los DDJJ que cambian: "
           f"{int(reclasificados['pozo_mes_ddjj_que_cambian'].sum())}")
    anotar("Regla por pozo = regla por pozo-mes (misma clasificación en todos los pozo-mes de los pozos reclasificados)",
           ok(reclasificados["pozo_mes_distintos_si_la_regla_fuera_por_pozo_mes"].sum() == 0),
           f"pozo-mes distintos: {int(reclasificados['pozo_mes_distintos_si_la_regla_fuera_por_pozo_mes'].sum())}")
    distintos = vm_vs_nc[(vm_vs_nc["dif_petroleo_m3"].abs() > 0.001) | (vm_vs_nc["dif_gas_miles_m3"].abs() > 0.001)]
    anotar("Vaca Muerta con los DDJJ vs. con el archivo no convencional (método anterior)", "EVIDENCIA",
           f"{len(distintos)} meses distintos" + ("" if distintos.empty else ": " + "; ".join(
               f"{f:%Y-%m} {r.dif_petroleo_m3:,.1f} m3 de petróleo y {r.dif_gas_miles_m3:,.1f} miles de m3 de gas"
               for f, r in distintos.iterrows())))

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
            con_dif = tabla[tabla[f"{c}_dif"].abs() > TOLERANCIA_SERIE]
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


def comparar_versiones_2026(petroleo, gas, anual_2026, fecha_serie_agregada: str) -> pd.DataFrame:
    """Serie agregada (versión publicada el fecha_serie_agregada) vs. archivo anual por pozo de 2026
    (más reciente), por mes, y lo cargado después de la serie agregada según fechaingreso."""
    a = anual_2026.copy()
    a["cargado_despues"] = pd.to_datetime(a["fechaingreso"], errors="coerce") > pd.Timestamp(fecha_serie_agregada[:10]) + pd.Timedelta(days=1)
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
                "dato_vigente_de": ("serie agregada de la SE" if serie != "petroleo_vaca_muerta" else
                                    "DDJJ abiertas y cerradas por pozo, con la clasificación más reciente de la SE")}
        if serie in columna_2026 and fecha in versiones.index:
            fila["pozo_a_pozo_anual_2026"] = versiones.loc[fecha, columna_2026[serie]]
            fila["revision_pct_pozo_a_pozo"] = 100 * (fila["pozo_a_pozo_anual_2026"] / valor - 1)
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
def leer_publicaciones_por_pozo(ultimo_mes_completo: pd.Timestamp, registros: list) -> tuple:
    """Lee los DDJJ abiertas y cerradas (vigentes y versiones anteriores) y el archivo no convencional
    (vigente y versiones anteriores). Devuelve: publicaciones (nombre -> (tabla compacta, fecha de
    publicación)), los volúmenes de los DDJJ vigentes (cada uno con su año y hasta el último mes
    completo), la tabla vigente del archivo no convencional y un resumen de los DDJJ."""
    publicaciones, volumenes, filas_de_otro_anio = {}, [], 0

    def agregar_versiones_anteriores(etiqueta, nombre_archivo, hash_vigente):
        for version in se.versiones_pozos(nombre_archivo):
            if version["sha256"] != hash_vigente:
                compacta = compactar_publicacion(se.leer_pozos_version(version["ruta"]))
                publicaciones[f"{etiqueta}, versión anterior {version['sha256'][:12]}"] = (compacta, version["fecha_publicacion"])

    for anio, (nombre_archivo, _) in se.POZOS_ANUAL_DDJJ.items():
        tabla, registro = se.descargar_pozos_anual_ddjj(anio)
        registros.append(registro)
        compacta = compactar_publicacion(tabla)
        del tabla
        publicaciones[f"DDJJ {anio}"] = (compacta, registro["fecha_publicacion"])
        filas_de_otro_anio += int((compacta["anio"] != anio).sum())
        volumenes.append(compacta.loc[(compacta["anio"] == anio) & (compacta["fecha"] <= ultimo_mes_completo),
                                      ["idpozo", "fecha", "prod_pet", "prod_gas", "clave"]])
        agregar_versiones_anteriores(f"DDJJ {anio}", nombre_archivo, registro["sha256"])
        print(f"    DDJJ {anio}: {len(compacta):,} filas (publicado {registro['fecha_publicacion'][:10]})", flush=True)

    pozos_nc, registro = se.descargar_pozos_no_convencional()
    registros.append(registro)
    publicaciones["No convencional"] = (compactar_publicacion(pozos_nc), registro["fecha_publicacion"])
    agregar_versiones_anteriores("No convencional", se.POZOS_NO_CONVENCIONAL[0], registro["sha256"])

    # Una sola tabla de volúmenes, con las claves como categoría común (los archivos traen categorías distintas).
    categorias = sorted(set().union(*(set(v["clave"].cat.categories) for v in volumenes)))
    volumenes = pd.concat([v.assign(clave=v["clave"].cat.set_categories(categorias)) for v in volumenes], ignore_index=True)
    resumen = {"pozo_mes": len(volumenes), "anios": f"{min(se.POZOS_ANUAL_DDJJ)}-{max(se.POZOS_ANUAL_DDJJ)}",
               "repetidos": int(volumenes.duplicated(["idpozo", "fecha"]).sum()), "filas_de_otro_anio": filas_de_otro_anio}
    return publicaciones, volumenes, pozos_nc, resumen


def sesco_mensual(tablas: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """SESCO: producción promedio diaria total del país (suma de las cuencas), petróleo en m3/d y gas
    en miles de m3/d, con índice mensual."""
    columnas = {}
    for clave, tabla in tablas.items():
        valor = [c for c in tabla.columns if c.startswith("produccion_")][0]
        columnas[f"{clave}_{valor}"] = tabla.groupby("indice_tiempo")[valor].sum()
    tabla = pd.DataFrame(columnas).reset_index()
    tabla.index = pd.PeriodIndex(tabla.pop("indice_tiempo"), freq="M").to_timestamp()
    tabla.index.name = "fecha"
    return tabla


def armar() -> dict:
    if not descargas.sin_red():
        # Antes de bajar nada: qué cambió en el portal; frena si no responde o si pasa 1 GB sin ok.
        se.autorizar_descarga(se.revisar_portal(se.archivos_produccion()))

    agregadas, registros = se.descargar_series_agregadas()
    petroleo, gas = agregadas["petroleo"], agregadas["gas"]
    fecha_serie_agregada = registros[0]["fecha_publicacion"]
    # Último mes completo de la fuente oficial: el último mes de la serie agregada de la SE.
    ultimo_mes_completo = min(petroleo.index.max(), gas.index.max())

    publicaciones, volumenes, pozos_nc, ddjj_resumen = leer_publicaciones_por_pozo(ultimo_mes_completo, registros)
    anuales = {}
    for anio in ANIOS_COBERTURA:
        anuales[anio], registro = se.descargar_pozos_anual(anio)
        registros.append(registro)
    anual_2026 = anuales[2026]
    tablas_sesco, regs = se.descargar_sesco_diaria()
    registros += regs
    sesco = sesco_mensual(tablas_sesco)

    # Clasificación vigente de cada pozo y volúmenes de los DDJJ.
    por_publicacion = pd.concat([clasificacion_por_publicacion(nombre, compacta, fecha)
                                 for nombre, (compacta, fecha) in publicaciones.items()], ignore_index=True)
    vigente = clasificacion_vigente(por_publicacion)
    atributos = atributos_claves(por_publicacion["clave"])
    clave_vigente = vigente["clave"].astype("category").reindex(volumenes["idpozo"]).reset_index(drop=True)
    vigentes = sumas_mensuales(volumenes, clave_vigente, atributos)
    propias = sumas_mensuales(volumenes, volumenes["clave"], atributos)
    verificacion = ddjj_vs_serie(vigentes, propias, petroleo, gas)
    reclasificados = reclasificaciones(por_publicacion, vigente, publicaciones, volumenes, atributos)

    nacional = armar_nacional(petroleo, gas)
    vaca_muerta = armar_vaca_muerta(vigentes, verificacion, ultimo_mes_completo)
    series = {"produccion_petroleo_gas_mensual": nacional, "produccion_vaca_muerta_mensual": vaca_muerta}
    verificar_corte(series, ultimo_mes_completo)  # si una serie se pasa del último mes completo, frena acá
    vm_vs_nc = vaca_muerta_vs_no_convencional(vaca_muerta, pozos_nc[pozos_nc["fecha"] <= ultimo_mes_completo])

    comparacion = comparar_no_convencional_con_serie(pozos_nc[pozos_nc["fecha"] <= ultimo_mes_completo], petroleo, gas)
    regla = evidencia_regla_sin_subtipo(comparacion)
    no_cierran = meses_que_no_cierran(comparacion)
    coberturas = {anio: cobertura(pozos_nc, anual, anio, ultimo_mes_completo) for anio, anual in anuales.items()}
    anuales_vs = {anio: anual_vs_serie(anual, petroleo, gas, anio, ultimo_mes_completo) for anio, anual in anuales.items()}
    versiones = comparar_versiones_2026(petroleo, gas, anual_2026, fecha_serie_agregada)
    tabla_controles = controles(petroleo, gas, nacional, comparacion, regla, coberturas, anuales_vs, anual_2026,
                                series, ultimo_mes_completo, verificacion, por_publicacion, reclasificados, vm_vs_nc, ddjj_resumen)
    difusion = contrastar_primera_difusion(nacional, vaca_muerta, versiones, sesco)

    fechas = {"date_format": "%Y-%m-%d"}
    return {
        "series": {"produccion_petroleo_gas_mensual.csv": nacional, "produccion_vaca_muerta_mensual.csv": vaca_muerta},
        "controles": tabla_controles,
        "validacion": {
            "produccion_ddjj_vs_serie.csv": (verificacion, {"float_format": "%.4f", **fechas}),
            "produccion_reclasificaciones.csv": (reclasificados, {"index": False, "float_format": "%.4f", **fechas}),
            "produccion_vaca_muerta_ddjj_vs_no_convencional.csv": (vm_vs_nc, {"float_format": "%.4f", **fechas}),
            "produccion_no_convencional_vs_serie.csv": (comparacion, {"float_format": "%.3f", **fechas}),
            "produccion_regla_sin_subtipo.csv": (regla, {"float_format": "%.3f", **fechas}),
            "produccion_meses_que_no_cierran.csv": (no_cierran, {"index": False, "float_format": "%.4f", **fechas}),
            "produccion_cobertura_no_convencional.csv": (pd.concat(coberturas.values()), {"float_format": "%.3f", **fechas}),
            "produccion_anuales_vs_serie.csv": (pd.concat(anuales_vs.values()), {"float_format": "%.3f", **fechas}),
            "produccion_versiones_2026.csv": (versiones, {"float_format": "%.3f", **fechas}),
            "produccion_vs_primera_difusion.csv": (difusion, {"index": False, "float_format": "%.3f"}),
            "descargas_produccion.csv": (pd.DataFrame(registros).drop(columns=["descargado"], errors="ignore"), {"index": False}),
        },
        "registros": registros,
    }
