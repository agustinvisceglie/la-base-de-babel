"""
Nota "La vuelta del gas". Control: capítulo 27 según la base comex del INDEC vs. cifras oficiales.

Qué hace: suma el capítulo 27 en la base de comercio exterior del INDEC (microdatos por posición
    NCM, comex.indec.gob.ar) para años seleccionados y lo compara con los anuales y acumulados
    oficiales que usa la nota. Sirve para documentar por qué esa base no se usa como fuente
    principal: desde 2018 el secreto estadístico tapa parte de las exportaciones del capítulo 27.
Fuentes: INDEC, bases exports_AAAA_M.zip e imports_AAAA_M.zip; datos/procesados/ica_anual.csv y
    cifras_para_el_texto.csv (generados por 1_ica.py, que tiene que correr antes).
Genera: validacion/cap27_comex_vs_oficial.csv y validacion/descargas_comex.csv

Uso (desde la raíz del repositorio):
    .venv/Scripts/python notas/2026-12-la-vuelta-del-gas/control_comex.py
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

import pandas as pd

from scripts import indec_comex
from scripts.descargas import PROCESADOS, guardar_registro

CARPETA_NOTA = Path(__file__).resolve().parent
VALIDACION = CARPETA_NOTA / "validacion"

# Años de muestra: dos anteriores al secreto estadístico (2018) y varios posteriores.
ANIOS_COMPLETOS = [2006, 2015, 2018, 2020, 2022, 2024, 2025]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    anual = pd.read_csv(PROCESADOS / "ica_anual.csv", index_col="anio")
    cifras = pd.read_csv(CARPETA_NOTA / "cifras_para_el_texto.csv", index_col="periodo")
    ultimo_acumulado = [p for p in cifras.index if "ene-" in p][-1]   # por ejemplo "2026 ene-sep"
    anio_en_curso = int(ultimo_acumulado[:4])

    filas, registros = [], []
    for anio in ANIOS_COMPLETOS + [anio_en_curso]:
        sumas = {}
        for flujo, clave in (("exports", "expo"), ("imports", "impo")):
            ruta, registro = indec_comex.descargar_base(flujo, anio)
            registros.append(registro)
            sumas[clave] = indec_comex.sumar_capitulo(ruta)
        if anio == anio_en_curso:
            meses = int(sumas["expo"].index.max())
            periodo, oficial = ultimo_acumulado, cifras.loc[ultimo_acumulado]
            fuente = "Acumulado oficial (cifras_para_el_texto.csv)"
        else:
            meses = 12
            periodo, oficial = str(anio), anual.loc[anio]
            fuente = anual.loc[anio, "fuente_cap27"]
        fila = {"periodo": periodo, "meses_en_base": meses,
                "expo_comex_musd": sumas["expo"].sum(), "expo_oficial_musd": oficial["expo_cap27_musd"],
                "impo_comex_musd": sumas["impo"].sum(), "impo_oficial_musd": oficial["impo_cap27_musd"],
                "referencia_oficial": fuente}
        fila["dif_expo_musd"] = fila["expo_comex_musd"] - fila["expo_oficial_musd"]
        fila["dif_expo_pct"] = 100 * fila["dif_expo_musd"] / fila["expo_oficial_musd"]
        fila["dif_impo_musd"] = fila["impo_comex_musd"] - fila["impo_oficial_musd"]
        filas.append(fila)
        print(f"{periodo}: expo comex {fila['expo_comex_musd']:8.1f} vs oficial {fila['expo_oficial_musd']:8.1f} "
              f"({fila['dif_expo_pct']:+.1f}%) | impo comex {fila['impo_comex_musd']:8.1f} vs oficial "
              f"{fila['impo_oficial_musd']:8.1f}")

    pd.DataFrame(filas).to_csv(VALIDACION / "cap27_comex_vs_oficial.csv", index=False, float_format="%.1f")
    guardar_registro(registros, VALIDACION / "descargas_comex.csv")


if __name__ == "__main__":
    main()
