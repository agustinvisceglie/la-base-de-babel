"""
Tests del armador de series de producción (series/produccion_hidrocarburos.py).

Qué hace: verifica que
    - el control de corte impida que un mes posterior al último mes completo de la fuente oficial
      entre a una serie (por ejemplo, el octubre de 2026 parcial del anual por pozo);
    - la clasificación de cada pozo salga de la publicación más reciente de la SE, que el volumen
      vaya al agregado de esa clasificación (con la regla "no convencional sin subtipo = tight") y
      que la lista de reclasificaciones mida bien el volumen que cambia.
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


# ---------------------------------------------------------------------------------------------
# Paso 1: clasificación de cada pozo según la publicación más reciente de la SE
# ---------------------------------------------------------------------------------------------
from series.produccion_hidrocarburos import (atributos_claves, clasificacion_por_publicacion, clasificacion_vigente,
                                             compactar_publicacion, reclasificaciones, sumas_mensuales)


def publicacion(filas):
    """Tabla por pozo mínima: (idpozo, mes de 2023, petróleo, gas, tipo, subtipo, formación)."""
    tabla = pd.DataFrame(filas, columns=["idpozo", "mes", "prod_pet", "prod_gas", "tipo_de_recurso", "sub_tipo_recurso", "formprod"])
    tabla["anio"] = 2023
    tabla["fecha"] = pd.to_datetime(dict(year=tabla["anio"], month=tabla["mes"], day=1))
    tabla["areayacimiento"] = "CAMPO X"
    tabla["cuenca"] = "NEUQUINA"
    return compactar_publicacion(tabla)


class TestClasificacionMasReciente(unittest.TestCase):
    def setUp(self):
        # El pozo 1 es convencional en el DDJJ (más viejo) y shale de Vaca Muerta en el archivo no
        # convencional (más nuevo), como el pozo de 2023 del instructivo. El pozo 2 es no convencional
        # sin subtipo (cuenta como tight) y solo está en el DDJJ.
        self.ddjj = publicacion([(1, 5, 0.0, 10.0, "CONVENCIONAL", None, "VMUT"),
                                 (1, 6, 0.0, 20.0, "CONVENCIONAL", None, "VMUT"),
                                 (2, 5, 7.0, 1.0, "NO CONVENCIONAL", None, "CSEC")])
        self.nc = publicacion([(1, 5, 0.0, 10.0, "NO CONVENCIONAL", "SHALE", "VMUT"),
                               (1, 6, 0.0, 20.0, "NO CONVENCIONAL", "SHALE", "VMUT")])
        self.publicaciones = {"DDJJ 2023": (self.ddjj, "2026-06-05T17:32:19"),
                              "No convencional": (self.nc, "2026-11-22T21:00:55")}
        self.por_publicacion = pd.concat([clasificacion_por_publicacion(n, c, f) for n, (c, f) in self.publicaciones.items()],
                                         ignore_index=True)
        self.vigente = clasificacion_vigente(self.por_publicacion)
        self.atributos = atributos_claves(self.por_publicacion["clave"])

    def test_gana_la_publicacion_mas_reciente(self):
        self.assertEqual(self.vigente.loc[1, "clave"], "NO CONVENCIONAL|SHALE|VMUT")
        self.assertEqual(self.vigente.loc[1, "publicacion"], "No convencional")
        self.assertEqual(self.vigente.loc[2, "clave"], "NO CONVENCIONAL||CSEC")

    def test_volumen_va_al_agregado_de_la_clasificacion_vigente(self):
        claves = self.vigente["clave"].astype("category").reindex(self.ddjj["idpozo"]).reset_index(drop=True)
        vigentes = sumas_mensuales(self.ddjj, claves, self.atributos)
        propias = sumas_mensuales(self.ddjj, self.ddjj["clave"], self.atributos)
        self.assertEqual(vigentes["gas_shale"].tolist(), [10.0, 20.0])
        self.assertEqual(vigentes["gas_vaca_muerta"].tolist(), [10.0, 20.0])
        self.assertEqual(propias["gas_shale"].tolist(), [0.0, 0.0])
        # No convencional sin subtipo = tight (regla de la SE)
        self.assertEqual(vigentes["petroleo_tight"].tolist(), [7.0, 0.0])

    def test_lista_de_reclasificaciones(self):
        lista = reclasificaciones(self.por_publicacion, self.vigente, self.publicaciones, self.ddjj, self.atributos)
        self.assertEqual(len(lista), 1)
        fila = lista.iloc[0]
        self.assertEqual(fila["idpozo"], 1)
        self.assertEqual(fila["que_cambia"], "tipo de recurso o subtipo")
        self.assertTrue(fila["cambia_vaca_muerta"])
        self.assertEqual(fila["pozo_mes_ddjj_que_cambian"], 2)
        self.assertAlmostEqual(fila["gas_miles_m3_que_cambia"], 30.0)
        self.assertEqual(fila["pozo_mes_distintos_si_la_regla_fuera_por_pozo_mes"], 0)

    def test_una_sola_clasificacion_por_pozo_en_cada_publicacion(self):
        self.assertTrue((self.por_publicacion["clasificaciones_en_la_publicacion"] == 1).all())
