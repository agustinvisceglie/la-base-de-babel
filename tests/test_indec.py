"""
Tests de los lectores de cuadros del INDEC (lectores/indec.py).

Qué hace: lee el cuadro 1 (acumulado del año) del Excel de cuadros de informes técnicos del ICA
    de distintos meses y lo compara con lo publicado en el PDF de cada informe. Cubre los meses en
    que la fila del acumulado se llama distinto: diciembre ("Total anual") y febrero ("Total
    bimestre"; "Primer bimestre" en el PDF), un mes común (septiembre, "Acumulado hasta...") y el
    formato nuevo del cuadro 1 (desde el informe del 19/11/2026: filas por mes y bloque "Acumulados").
Fuentes: Excel de cuadros del ICA (www.indec.gob.ar/ftp/cuadros/economia/ica_cuadros_DD_MM_AA.xls;
    se usa la versión guardada en datos/crudos/indec/versiones/; si no hay, se baja con la descarga
    condicional) y los valores del cuadro 1 del PDF de cada informe,
    copiados abajo con la página. Los PDF redondean a millones: la tolerancia es 1.
Genera: nada (solo dice si los tests pasan).

Uso (desde la raíz del repositorio):
    .venv/Scripts/python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))  # para poder importar lectores/ y comun/

import pandas as pd

from comun import descargas
from lectores import indec

TOLERANCIA_MUSD = 1.0

# Cuadro 1 publicado en el PDF de cada informe: {(año en curso o anterior, flujo): valor}.
CASOS_CUADRO1 = [
    {
        "archivo": "ica_cuadros_20_01_26.xls",
        "mes": pd.Timestamp("2025-12-01"),
        "pdf": "https://www.indec.gob.ar/uploads/informesdeprensa/ica_01_26ABE4F7373E.pdf, p. 7, fila 'Total anual'",
        "publicado": {("actual", "expo"): 87077, ("actual", "impo"): 75791, ("actual", "saldo"): 11286,
                      ("anterior", "expo"): 79703, ("anterior", "impo"): 60776, ("anterior", "saldo"): 18928},
    },
    {
        "archivo": "ica_cuadros_19_03_26.xls",
        "mes": pd.Timestamp("2026-02-01"),
        "pdf": "https://www.indec.gob.ar/uploads/informesdeprensa/ica_03_26F8A1F5EA02.pdf, p. 7, fila 'Primer bimestre'",
        "publicado": {("actual", "expo"): 13208, ("actual", "impo"): 10231, ("actual", "saldo"): 2977,
                      ("anterior", "expo"): 12055, ("anterior", "impo"): 11617, ("anterior", "saldo"): 438},
    },
    {
        "archivo": "ica_cuadros_19_10_26.xls",
        "mes": pd.Timestamp("2026-09-01"),
        "pdf": "https://www.indec.gob.ar/uploads/informesdeprensa/ica_10_263F42E3F39F.pdf, p. 7, fila 'Acumulado hasta septiembre'",
        "publicado": {("actual", "expo"): 77267, ("actual", "impo"): 56069, ("actual", "saldo"): 21198,
                      ("anterior", "saldo"): 6046},
    },
    {   # Primer informe con el formato nuevo del cuadro 1 (filas por mes; bloques "Mensuales" y "Acumulados").
        "archivo": "ica_cuadros_19_11_26.xls",
        "mes": pd.Timestamp("2026-10-01"),
        "pdf": "https://www.indec.gob.ar/uploads/informesdeprensa/ica_11_262BEEC7410A.pdf, p. 4, filas 'Octubre', columnas 'Acumulados'",
        "publicado": {("actual", "expo"): 87328, ("actual", "impo"): 62760, ("actual", "saldo"): 24568,
                      ("anterior", "expo"): 71496, ("anterior", "impo"): 64637, ("anterior", "saldo"): 6859},
    },
]


def ruta_cuadros(archivo: str) -> Path:
    """Devuelve la versión guardada del Excel de cuadros; si no hay ninguna, lo baja del INDEC."""
    try:
        return descargas.RAIZ / descargas.version_registrada(f"datos/crudos/indec/{archivo}")["version"]
    except descargas.DescargaFrenada:
        return indec.descargar_archivo(f"{indec.URL_INDEC}/ftp/cuadros/economia/{archivo}")[0]


class TestLeerCuadro1Acumulado(unittest.TestCase):
    def test_acumulado_igual_al_pdf(self):
        for caso in CASOS_CUADRO1:
            with self.subTest(archivo=caso["archivo"]):
                leido = indec.leer_cuadro1_acumulado(ruta_cuadros(caso["archivo"]))
                self.assertEqual(leido["mes"], caso["mes"])
                for (clave, flujo), publicado in caso["publicado"].items():
                    self.assertAlmostEqual(leido[clave][flujo], publicado, delta=TOLERANCIA_MUSD,
                                           msg=f"{clave}, {flujo} vs {caso['pdf']}")

    def test_coincide_con_los_cuadros_de_rubros_y_usos(self):
        """Control cruzado dentro del mismo Excel: los totales del cuadro 1 tienen que ser los de
        los cuadros de exportaciones por rubro e importaciones por uso (otra hoja, otro lector)."""
        for caso in CASOS_CUADRO1:
            with self.subTest(archivo=caso["archivo"]):
                ruta = ruta_cuadros(caso["archivo"])
                cuadro1, rubros_usos = indec.leer_cuadro1_acumulado(ruta), indec.leer_cuadro_rubros_usos(ruta)
                self.assertEqual(cuadro1["mes"], rubros_usos["mes"])
                for clave in ("actual", "anterior"):
                    self.assertAlmostEqual(cuadro1[clave]["expo"], rubros_usos["acumulado"][clave]["expo_total"], delta=0.01)
                    self.assertAlmostEqual(cuadro1[clave]["impo"], rubros_usos["acumulado"][clave]["impo_total"], delta=0.01)


if __name__ == "__main__":
    unittest.main()
