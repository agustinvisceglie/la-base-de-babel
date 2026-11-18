"""
Tests del armador de series de producción (series/produccion_hidrocarburos.py).

Qué hace: verifica que el control de corte impida que un mes posterior al último mes completo de
    la fuente oficial entre a una serie (por ejemplo, el octubre de 2026 parcial del anual por pozo).
Fuentes: ninguna (usa tablas armadas en el test).
Genera: nada.

Uso (desde la raíz del repositorio):
    .venv/Scripts/python -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import pandas as pd

from series.produccion_hidrocarburos import verificar_corte


def serie_mensual(desde: str, hasta: str) -> pd.DataFrame:
    fechas = pd.date_range(desde, hasta, freq="MS")
    return pd.DataFrame({"petroleo_m3_mes": range(len(fechas))}, index=fechas)


class TestVerificarCorte(unittest.TestCase):
    ultimo_mes_completo = pd.Timestamp("2026-09-01")

    def test_serie_hasta_el_ultimo_mes_completo_pasa(self):
        verificar_corte({"vaca_muerta": serie_mensual("2026-01-01", "2026-09-01")}, self.ultimo_mes_completo)

    def test_serie_con_un_mes_posterior_se_frena(self):
        with self.assertRaises(ValueError):
            verificar_corte({"vaca_muerta": serie_mensual("2026-01-01", "2026-10-01")}, self.ultimo_mes_completo)


if __name__ == "__main__":
    unittest.main()
