"""
Bloque 2, energía: balanza comercial energética (saldo CyE - CyL).

Qué hace (criterios, sección 1; migrado de la nota "La vuelta del gas" en el Paso 3b):
    - Saldo energético = exportaciones de Combustibles y energía (CyE) menos importaciones de
      Combustibles y lubricantes (CyL), del ICA del INDEC: mensual desde 2004 y anual oficial. Lee
      las series del bloque de sector externo (no baja nada).
    - Validación (datos/validacion/energia/):
        * cye_cyl_anual_vs_informes: anual vigente vs. lo publicado en los informes de diciembre
          (primera publicación y versión revisada un año después), desde 2022;
        * cye_cyl_vs_referencias_publicadas: el saldo publicado por terceros (2022 = -4.470;
          2024 = 5.668; 2025 = 7.815; ene-ago 2026 = 7.834) vs. la primera publicación del INDEC
          (tiene que coincidir) y vs. el dato vigente (la diferencia son revisiones);
        * comparacion_cye_cyl_vs_cap27: CyE - CyL vs. el capítulo 27 de la NCM (control), anual y
          acumulado del último informe.

Fuentes: datos/series/sector_externo/ (ica_mensual, ica_anual e ica_acumulados_informes), que arma
    bloques/sector_externo/comercio_exterior.py con el ICA del INDEC.
Genera (lo escribe actualizar.py): datos/series/energia/balanza_energetica_*.csv y datos/validacion/energia/*.csv.
"""

from __future__ import annotations

import pandas as pd

from comun.catalogo import leer_serie

PRIMER_ANIO_CONTRASTE = 2022
TOLERANCIA_MUSD = 1.0  # los informes redondean a millones enteros
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

# Saldo CyE - CyL publicado por terceros (valores de referencia validados en el chat del proyecto;
# criterios, sección 1, y auditoria-etapa-1-ica.md). (período, año, hasta el mes, saldo, CyE, CyL, quién)
REFERENCIAS_SALDO_CYE_CYL = [
    ("2022", 2022, 12, -4470, 8398, 12868, "IAE Mosconi y Más Energía"),
    ("2024", 2024, 12, 5668, None, None, "Secretaría de Energía"),
    ("2025", 2025, 12, 7815, None, None, "IARAF (N. Argañaraz)"),
    ("2026 ene-ago", 2026, 8, 7834, None, None, "Economía & Energía (N. Arceo) y RICSA ALyC"),
]

_COMUN = {"unidad": "millones de USD corrientes (exportaciones FOB menos importaciones CIF)", "tipo": "saldo",
          "precios": "corrientes", "ajuste_estacional": "original", "uso": "base", "organismo": "INDEC", "rotulo": "oficial",
          "fuente_url": "https://www.indec.gob.ar/Institucional/Indec/InformesTecnicos/40", "lector": "lectores/indec.py",
          "criterio": "§1 Balanza comercial energética: saldo = CyE - CyL, del ICA del INDEC", "estimados": "no",
          "tiene_revisiones": "sí: el INDEC revisa los meses y años recientes (ver la validación)", "discontinuada": "no",
          "con_reservas": "no", "informe_validacion": "datos/validacion/sector_externo/informe_validacion.md"}
SERIES = [
    {"archivo": "balanza_energetica_mensual.csv", "columna": "saldo_cye_cyl_musd", "frecuencia": "mensual",
     "nombre": "Saldo comercial energético (CyE - CyL)", "fuente_id": "datos/series/sector_externo/ica_mensual.csv (CyE y CyL)", **_COMUN},
    {"archivo": "balanza_energetica_anual.csv", "columna": "saldo_cye_cyl_musd", "frecuencia": "anual",
     "nombre": "Saldo comercial energético (CyE - CyL), anual", "fuente_id": "datos/series/sector_externo/ica_anual.csv (CyE y CyL)", **_COMUN},
]
AUXILIARES = {"balanza_energetica_anual.csv": ["provisorio"]}
DEPENDE_DE = ["sector_externo.ica_mensual.expo_cye_musd", "sector_externo.ica_mensual.impo_cyl_musd",
              "sector_externo.ica_anual.expo_cye_musd", "sector_externo.ica_anual.impo_cyl_musd",
              "sector_externo.ica_acumulados_informes.acum_expo_cye_musd"]
FORMATO = {"balanza_energetica_mensual.csv": "%.8f", "balanza_energetica_anual.csv": "%.8f"}  # la fuente trae centavos de USD


def leer_sector_externo() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    mensual = leer_serie("sector_externo", "ica_mensual.csv")
    anual = leer_serie("sector_externo", "ica_anual.csv", indice_fecha=False)
    acumulados = leer_serie("sector_externo", "ica_acumulados_informes.csv")
    acumulados["mes_informe"] = pd.to_datetime(acumulados["mes_informe"])
    return mensual, anual, acumulados


def etiqueta_acumulado(mes: pd.Timestamp, anio: int) -> str:
    return f"{anio} ene-{MESES[mes.month - 1]}"


def anual_vs_informes(anual: pd.DataFrame, acumulados: pd.DataFrame, anios: list[int]) -> pd.DataFrame:
    """CyE - CyL anual vigente vs. los informes de diciembre (salen en enero): primera publicación
    (informe de enero del año siguiente, columna del año en curso) y revisión un año después (informe
    de enero de dos años después, columna del año anterior). Diferencias: vigente menos informe."""
    filas = []
    for anio in anios:
        for version, anio_publicacion, prefijo in (("primera publicación", anio + 1, "acum"), ("revisada un año después", anio + 2, "acum_ant")):
            base = {"anio": anio, "version": version}
            informe = acumulados[acumulados["mes_informe"] == pd.Timestamp(anio_publicacion - 1, 12, 1)]
            if informe.empty:
                filas.append({**base, "estado": "TODAVIA NO PUBLICADO"})
                continue
            fecha, fila_informe = informe.index[0], informe.iloc[0]
            base["informe"] = f"{fecha:%d/%m/%Y}"
            fila = {**base, "hojas": f"{fila_informe['hoja_expo']} y {fila_informe['hoja_impo']}",
                    "expo_cye_informe": fila_informe[f"{prefijo}_expo_cye_musd"], "impo_cyl_informe": fila_informe[f"{prefijo}_impo_cyl_musd"]}
            fila["saldo_informe"] = fila["expo_cye_informe"] - fila["impo_cyl_informe"]
            fila["expo_cye_vigente"] = anual.loc[anio, "expo_cye_musd"]
            fila["impo_cyl_vigente"] = anual.loc[anio, "impo_cyl_musd"]
            fila["saldo_vigente"] = anual.loc[anio, "saldo_cye_cyl_musd"]
            fila["dif_expo_cye"] = fila["expo_cye_vigente"] - fila["expo_cye_informe"]
            fila["dif_impo_cyl"] = fila["impo_cyl_vigente"] - fila["impo_cyl_informe"]
            fila["dif_saldo"] = fila["saldo_vigente"] - fila["saldo_informe"]
            fila["estado"] = "OK" if abs(fila["dif_saldo"]) <= TOLERANCIA_MUSD else "REVISION POSTERIOR DEL INDEC"
            filas.append(fila)
    return pd.DataFrame(filas)


def referencias(anuales: pd.DataFrame, acumulados: pd.DataFrame, mensual: pd.DataFrame, anual: pd.DataFrame) -> pd.DataFrame:
    """Saldo CyE - CyL publicado por terceros vs. la primera publicación del INDEC (tiene que coincidir,
    salvo redondeo) y vs. el dato vigente (la diferencia son revisiones)."""
    filas = []
    for periodo, anio, hasta_mes, referencia, ref_expo, ref_impo, quien in REFERENCIAS_SALDO_CYE_CYL:
        if hasta_mes == 12:
            pub = anuales[(anuales["anio"] == anio) & (anuales["version"] == "primera publicación")].iloc[0]
            primera, informe = pub["saldo_informe"], f"informe ICA del {pub['informe']} (hojas {pub['hojas']})"
            expo_primera, impo_primera = pub["expo_cye_informe"], pub["impo_cyl_informe"]
            expo_vig, impo_vig = anual.loc[anio, "expo_cye_musd"], anual.loc[anio, "impo_cyl_musd"]
            fuente_vigente = "anual oficial vigente (cuadros anuales por rubro y uso)"
        else:
            fila_informe = acumulados[acumulados["mes_informe"] == pd.Timestamp(anio, hasta_mes, 1)].iloc[0]
            fecha = acumulados[acumulados["mes_informe"] == pd.Timestamp(anio, hasta_mes, 1)].index[0]
            expo_primera, impo_primera = fila_informe["acum_expo_cye_musd"], fila_informe["acum_impo_cyl_musd"]
            primera = expo_primera - impo_primera
            informe = f"informe ICA del {fecha:%d/%m/%Y} (hojas {fila_informe['hoja_expo']} y {fila_informe['hoja_impo']})"
            meses = mensual.loc[f"{anio}-01-01":f"{anio}-{hasta_mes:02d}-01"]
            expo_vig, impo_vig = meses["expo_cye_musd"].sum(), meses["impo_cyl_musd"].sum()
            fuente_vigente = f"suma de ene-{hasta_mes:02d} de la serie mensual vigente (control, no para citar)"
        difs = [primera - referencia] + ([expo_primera - ref_expo, impo_primera - ref_impo] if ref_expo is not None else [])
        filas.append({
            "periodo": periodo, "referencia_publicada": referencia, "publicado_por": quien,
            "referencia_expo_cye": ref_expo, "referencia_impo_cyl": ref_impo,
            "primera_publicacion_indec": primera, "expo_cye_primera": expo_primera, "impo_cyl_primera": impo_primera,
            "fuente_primera_publicacion": informe, "dif_primera_vs_referencia": primera - referencia,
            "estado": "OK" if max(abs(d) for d in difs) <= TOLERANCIA_MUSD else "REVISAR",
            "vigente": expo_vig - impo_vig, "fuente_vigente": fuente_vigente,
            "dif_vigente_vs_referencia": expo_vig - impo_vig - referencia,
            "dif_expo_cye_vigente_vs_primera": expo_vig - expo_primera, "dif_impo_cyl_vigente_vs_primera": impo_vig - impo_primera,
        })
    return pd.DataFrame(filas)


def comparar_con_cap27(anual: pd.DataFrame, acumulados: pd.DataFrame) -> pd.DataFrame:
    """Control: CyE - CyL vs. capítulo 27, anual (2004 al último año completo) y acumulado del último informe."""
    columnas = ["expo_cye_musd", "expo_cap27_musd", "impo_cyl_musd", "impo_cap27_musd", "saldo_cye_cyl_musd", "saldo_cap27_musd"]
    ultimo = acumulados.loc[acumulados.index.max()]
    mes = ultimo["mes_informe"]
    tabla = anual.loc[2004:mes.year - 1, columnas].copy()
    tabla.index = [str(a) for a in tabla.index]
    for anio, prefijo in ((mes.year - 1, "acum_ant"), (mes.year, "acum")):
        expo_cye, impo_cyl = ultimo[f"{prefijo}_expo_cye_musd"], ultimo[f"{prefijo}_impo_cyl_musd"]
        tabla.loc[etiqueta_acumulado(mes, anio)] = [expo_cye, ultimo[f"{prefijo}_expo_cap27_musd"], impo_cyl,
                                                    ultimo[f"{prefijo}_impo_cap27_musd"], expo_cye - impo_cyl, ultimo[f"{prefijo}_saldo_cap27_musd"]]
    tabla["dif_saldo_musd"] = tabla["saldo_cye_cyl_musd"] - tabla["saldo_cap27_musd"]
    tabla["dif_expo_musd"] = tabla["expo_cye_musd"] - tabla["expo_cap27_musd"]
    tabla["dif_impo_musd"] = tabla["impo_cyl_musd"] - tabla["impo_cap27_musd"]
    tabla.index.name = "periodo"
    return tabla


def armar() -> dict:
    mensual, anual_se, acumulados = leer_sector_externo()
    saldo_mensual = pd.DataFrame({"saldo_cye_cyl_musd": mensual["expo_cye_musd"] - mensual["impo_cyl_musd"]})
    saldo_mensual.index.name = "fecha"
    saldo_anual = pd.DataFrame({"saldo_cye_cyl_musd": anual_se["expo_cye_musd"] - anual_se["impo_cyl_musd"],
                                "provisorio": anual_se["provisorio"]})
    saldo_anual.index.name = "anio"
    anual = anual_se.join(saldo_anual[["saldo_cye_cyl_musd"]])

    anio_completo = acumulados.loc[acumulados.index.max(), "mes_informe"].year - 1
    anuales = anual_vs_informes(anual, acumulados, list(range(PRIMER_ANIO_CONTRASTE, anio_completo + 1)))
    refs = referencias(anuales, acumulados, mensual, anual)
    vs_cap27 = comparar_con_cap27(anual, acumulados)

    faltan = pd.date_range(saldo_mensual.index.min(), saldo_mensual.index.max(), freq="MS").difference(saldo_mensual.index)
    controles = [
        {"control": "Saldo energético mensual sin meses faltantes", "estado": "OK" if len(faltan) == 0 else "REVISAR",
         "detalle": f"{saldo_mensual.index.min():%m/%Y} a {saldo_mensual.index.max():%m/%Y}"},
        {"control": "Saldo CyE - CyL publicado por terceros = primera publicación del INDEC (-4.470, 5.668, 7.815, 7.834)",
         "estado": "OK" if (refs["estado"] == "OK").all() else "REVISAR",
         "detalle": "; ".join(f"{r.periodo}: {r.primera_publicacion_indec:.1f} vs {r.referencia_publicada}" for r in refs.itertuples())},
        {"control": "Primera publicación vs. dato vigente del saldo CyE - CyL (revisiones del INDEC)", "estado": "EVIDENCIA",
         "detalle": "; ".join(f"{r.anio} {r.version}: {r.dif_saldo:+.1f}" for r in anuales.dropna(subset=["dif_saldo"]).itertuples())},
    ]
    return {
        "series": {"balanza_energetica_mensual.csv": saldo_mensual, "balanza_energetica_anual.csv": saldo_anual},
        "controles": pd.DataFrame(controles),
        "validacion": {
            "cye_cyl_anual_vs_informes.csv": (anuales, {"index": False, "float_format": "%.2f"}),
            "cye_cyl_vs_referencias_publicadas.csv": (refs, {"index": False, "float_format": "%.2f"}),
            "comparacion_cye_cyl_vs_cap27.csv": (vs_cap27, {"float_format": "%.1f"}),
        },
    }
