"""
Nota "La vuelta del gas" (El Pozo y el Péndulo, diciembre 2026). Etapa 1: saldo energético.

EN PAUSA desde el 25/11/2026 (la nota 1 cambió de pregunta: ver nota-1-estructura.md). Desde el
Paso 3b del instructivo este script ya no arma series: lee solo la base (datos/series/) y arma lo
propio de la nota, con su corte. Las series, sus controles y su validación están en la base:
    - datos/series/sector_externo/ (bloques/sector_externo/comercio_exterior.py) y
      datos/validacion/sector_externo/;
    - datos/series/energia/balanza_energetica_*.csv (bloques/energia/balanza_energetica.py) y
      datos/validacion/energia/.

Pregunta de la nota: ¿cuánto del saldo comercial de bienes de la Argentina explica hoy la energía,
y cuánto de eso es estructural (más producción) y cuánto coyuntural (precios internacionales)?

Definición del saldo energético (criterios, sección 1): exportaciones de Combustibles y energía (CyE)
menos importaciones de Combustibles y lubricantes (CyL), del ICA del INDEC.

Qué hace:
    1. g1: CyE, CyL y saldo por año (anuales oficiales, 2004 al último año completo) más el mismo
       período acumulado del año anterior y del año en curso (acumulados oficiales del informe del
       mes de corte).
    2. g2: saldo energético y saldo comercial de bienes, suma de 12 meses, mensual hasta el corte.
    3. Cifras para citar en el texto: solo anuales y acumulados oficiales (nunca suma de meses).
    4. Control propio: los 12 meses derivados de cifras oficiales = el último punto de g2.

Corte: MES_DE_CORTE (septiembre de 2026, informe del ICA del 19/10/2026). La base guarda hasta el
último mes de la fuente; la nota usa hasta su corte, y los acumulados del informe de ese mes.
Nota congelada: el README registra el commit de la base con que se armaron g1, g2 y las cifras.

Fuentes: datos/series/sector_externo/ica_mensual.csv, ica_anual.csv e ica_acumulados_informes.csv,
    y datos/series/energia/balanza_energetica_mensual.csv y balanza_energetica_anual.csv.
Genera:
    - cifras_para_el_texto.csv
    - graficos/g1_balanza_energetica_anual.csv y .png
    - graficos/g2_saldo_energetico_vs_total_12m.csv y .png
    - validacion/controles_nota.csv

Uso (desde la raíz del repositorio):
    .venv/Scripts/python notas/2026-12-la-vuelta-del-gas/1_ica.py
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))  # para poder importar comun/ al correr este archivo directamente

import matplotlib

matplotlib.use("Agg")  # sin ventanas: solo guarda los PNG
import matplotlib.pyplot as plt
import pandas as pd

from comun.catalogo import leer_serie

CARPETA_NOTA = Path(__file__).resolve().parent
GRAFICOS = CARPETA_NOTA / "graficos"
VALIDACION = CARPETA_NOTA / "validacion"

PRIMER_ANIO_NOTA = 2004  # comienzo de la serie mensual oficial por rubros y usos
MES_DE_CORTE = pd.Timestamp("2026-09-01")  # último mes que usa la nota (informe ICA del 19/10/2026)
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
COLUMNAS_ENERGIA = ["expo_cye_musd", "impo_cyl_musd", "saldo_cye_cyl_musd"]


# ---------------------------------------------------------------------------------------------
# 1. Lectura de la base
# ---------------------------------------------------------------------------------------------
def leer_base() -> dict:
    mensual = leer_serie("sector_externo", "ica_mensual.csv").join(leer_serie("energia", "balanza_energetica_mensual.csv"))
    anual = leer_serie("sector_externo", "ica_anual.csv", indice_fecha=False).join(
        leer_serie("energia", "balanza_energetica_anual.csv", indice_fecha=False)[["saldo_cye_cyl_musd"]])
    acumulados = leer_serie("sector_externo", "ica_acumulados_informes.csv")
    acumulados["mes_informe"] = pd.to_datetime(acumulados["mes_informe"])

    if mensual.index.max() < MES_DE_CORTE:
        raise ValueError(f"La base llega a {mensual.index.max():%m/%Y}: todavía no tiene el mes de corte ({MES_DE_CORTE:%m/%Y})")
    del_corte = acumulados[acumulados["mes_informe"] == MES_DE_CORTE].sort_index()
    if del_corte.empty:
        raise ValueError(f"La base no tiene el informe del mes de corte ({MES_DE_CORTE:%m/%Y})")
    # Si hubiera más de un informe de ese mes, el primero publicado (el del corte).
    corte = del_corte.iloc[0].copy()
    corte["fecha_publicacion"] = del_corte.index[0]
    return {"ica": mensual.loc[:MES_DE_CORTE], "anual": anual, "corte": corte}


# ---------------------------------------------------------------------------------------------
# 2. Gráficos y cifras para el texto
# ---------------------------------------------------------------------------------------------
def etiqueta_acumulado(mes: pd.Timestamp, anio: int) -> str:
    return f"{anio} ene-{MESES[mes.month - 1]}"


def acumulado_energia(corte: pd.Series, prefijo: str) -> list[float]:
    """CyE, CyL y saldo CyE - CyL acumulados del informe del corte ("acum" = año en curso, "acum_ant" = anterior)."""
    expo, impo = corte[f"{prefijo}_expo_cye_musd"], corte[f"{prefijo}_impo_cyl_musd"]
    return [expo, impo, expo - impo]


def armar_g1(anual: pd.DataFrame, corte: pd.Series) -> pd.DataFrame:
    """Años completos (anual oficial) + mismo período acumulado del año anterior y del año en curso."""
    mes = corte["mes_informe"]
    anio_completo = mes.year if mes.month == 12 else mes.year - 1
    g1 = anual.loc[PRIMER_ANIO_NOTA:anio_completo, COLUMNAS_ENERGIA].copy()
    if g1.isna().any().any() or g1.index.max() != anio_completo:
        raise ValueError(f"Faltan anuales oficiales de CyE o CyL entre {PRIMER_ANIO_NOTA} y {anio_completo}")
    g1.index = [str(a) for a in g1.index]
    if mes.month < 12:
        for anio, prefijo in ((mes.year - 1, "acum_ant"), (mes.year, "acum")):
            g1.loc[etiqueta_acumulado(mes, anio)] = acumulado_energia(corte, prefijo)
    g1.index.name = "periodo"
    return g1


def armar_g2(ica: pd.DataFrame) -> pd.DataFrame:
    """Saldo energético y saldo comercial de bienes, suma móvil de 12 meses (desde diciembre de 2004)."""
    g2 = pd.DataFrame({
        "saldo_cye_cyl_12m_musd": ica["saldo_cye_cyl_musd"].rolling(12).sum(),
        "saldo_comercial_bienes_12m_musd": ica["saldo_total_musd"].rolling(12).sum(),
    }).dropna()
    g2.index.name = "fecha"
    return g2


def armar_cifras_para_el_texto(anual: pd.DataFrame, corte: pd.Series) -> pd.DataFrame:
    """Cifras citables, solo de anuales y acumulados oficiales (no se suman meses)."""
    mes = corte["mes_informe"]
    mes_texto = MESES[mes.month - 1]
    fecha_informe = f"{corte['fecha_publicacion']:%d/%m/%Y}"
    anio_completo = mes.year - 1

    filas = []
    for anio in range(anio_completo - 2, anio_completo + 1):
        fila = anual.loc[anio]
        filas.append({
            "periodo": str(anio),
            **dict(zip(COLUMNAS_ENERGIA, fila[COLUMNAS_ENERGIA])), "saldo_comercial_bienes_musd": fila["saldo_total_musd"],
            "fuente": f"Anual oficial{' (provisorio)' if fila['provisorio'] else ''}: INDEC, "
                      f"{fila['archivo_expo_rubros']} (CyE y exportaciones totales) e "
                      f"{fila['archivo_impo_usos']} (CyL e importaciones totales)",
        })
    for anio, prefijo in ((mes.year - 1, "acum_ant"), (mes.year, "acum")):
        filas.append({
            "periodo": etiqueta_acumulado(mes, anio),
            **dict(zip(COLUMNAS_ENERGIA, acumulado_energia(corte, prefijo))),
            "saldo_comercial_bienes_musd": corte[f"{prefijo}_saldo_total_musd"],
            "fuente": f"Acumulado oficial del informe ICA del {fecha_informe} (hojas {corte['hoja_expo']} y "
                      f"{corte['hoja_impo']} del Excel de cuadros; saldo de bienes, cuadro 1)",
        })
    # Últimos 12 meses = año completo anterior + acumulado del año en curso - mismo acumulado del año anterior.
    anio_anterior, acum_anio_anterior, acum_anio_actual = filas[2], filas[3], filas[4]
    filas.append({
        "periodo": f"12 meses a {mes_texto}-{mes.year}",
        **{col: anio_anterior[col] + acum_anio_actual[col] - acum_anio_anterior[col]
           for col in COLUMNAS_ENERGIA + ["saldo_comercial_bienes_musd"]},
        "fuente": f"Derivado de oficiales: {anio_completo} + ene-{mes_texto} {mes.year} - ene-{mes_texto} {mes.year - 1}",
    })
    cifras = pd.DataFrame(filas).set_index("periodo")
    # Si los dos saldos tienen signos distintos, el cociente no es un "peso": la celda queda vacía.
    signos_distintos = (cifras["saldo_cye_cyl_musd"] > 0) != (cifras["saldo_comercial_bienes_musd"] > 0)
    peso = 100 * cifras["saldo_cye_cyl_musd"] / cifras["saldo_comercial_bienes_musd"]
    cifras.insert(4, "peso_saldo_energetico_pct", peso.mask(signos_distintos))
    cifras.insert(5, "nota", ["Signos distintos: no se calcula el peso" if s else "" for s in signos_distintos])
    return cifras


def guardar_png_g1(g1: pd.DataFrame, ruta: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 5))
    g1[["expo_cye_musd", "impo_cyl_musd"]].plot.bar(ax=ax, width=0.8)
    ax.plot(range(len(g1)), g1["saldo_cye_cyl_musd"], color="black", marker="o", label="saldo_cye_cyl_musd")
    ax.axhline(0, color="grey", linewidth=0.8)
    ax.set_title("g1. Balanza comercial energética, CyE - CyL (millones de USD) - control rápido")
    ax.legend()
    fig.tight_layout()
    fig.savefig(ruta, dpi=100)
    plt.close(fig)


def guardar_png_g2(g2: pd.DataFrame, ruta: Path) -> None:
    fig, ax = plt.subplots(figsize=(12, 5))
    g2.plot(ax=ax)
    ax.axhline(0, color="grey", linewidth=0.8)
    ax.set_title("g2. Saldo energético (CyE - CyL) vs. saldo comercial de bienes, 12 meses (millones de USD) - control rápido")
    fig.tight_layout()
    fig.savefig(ruta, dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------------------------
def main():
    sys.stdout.reconfigure(encoding="utf-8")
    GRAFICOS.mkdir(exist_ok=True)
    VALIDACION.mkdir(exist_ok=True)
    base = leer_base()

    g1 = armar_g1(base["anual"], base["corte"])
    g1.to_csv(GRAFICOS / "g1_balanza_energetica_anual.csv", float_format="%.1f")
    guardar_png_g1(g1, GRAFICOS / "g1_balanza_energetica_anual.png")
    g2 = armar_g2(base["ica"])
    g2.to_csv(GRAFICOS / "g2_saldo_energetico_vs_total_12m.csv", float_format="%.1f", date_format="%Y-%m-%d")
    guardar_png_g2(g2, GRAFICOS / "g2_saldo_energetico_vs_total_12m.png")
    cifras = armar_cifras_para_el_texto(base["anual"], base["corte"])
    cifras.to_csv(CARPETA_NOTA / "cifras_para_el_texto.csv", float_format="%.1f")

    doce_meses = cifras.iloc[-1]
    dif_12m = max(abs(doce_meses["saldo_cye_cyl_musd"] - g2["saldo_cye_cyl_12m_musd"].iloc[-1]),
                  abs(doce_meses["saldo_comercial_bienes_musd"] - g2["saldo_comercial_bienes_12m_musd"].iloc[-1]))
    controles = pd.DataFrame([
        {"control": f"12 meses derivado de oficiales = último punto de g2 ({g2.index[-1]:%m/%Y})",
         "estado": "OK" if dif_12m < 0.01 else "REVISAR", "detalle": f"diferencia máxima {dif_12m:.6f} MUSD"},
        {"control": "La base tiene el informe del mes de corte", "estado": "OK",
         "detalle": f"informe ICA del {base['corte']['fecha_publicacion']:%d/%m/%Y} ({MES_DE_CORTE:%m/%Y})"},
    ])
    controles.to_csv(VALIDACION / "controles_nota.csv", index=False)

    pd.set_option("display.width", 250)
    print(f"Base: mensual hasta {base['ica'].index.max():%m/%Y} (corte de la nota); informe del corte: "
          f"{base['corte']['fecha_publicacion']:%d/%m/%Y}")
    print("\nCifras para el texto (solo oficiales):\n" + cifras.drop(columns="fuente").round(1).to_string())
    print("\nControles de la nota:\n" + controles.to_string(index=False))
    print("\nRESULTADO:", "HAY CONTROLES PARA REVISAR" if (controles["estado"] != "OK").any() else "todos los controles OK")


if __name__ == "__main__":
    main()
