"""
Tests de la descarga condicional de la SE (scripts/secretaria_energia.py y scripts/descargas.py).

Qué hace: verifica que
    - si la API del portal no informa la fecha de publicación, no se baja nada y se frena con la
      lista de archivos sin verificar y su tamaño total;
    - si lo que cambió supera 1 GB, se frena salvo que haya ok (regla 8 del instructivo);
    - si el portal republica el mismo contenido con otra fecha, no se copia otra versión pero se
      anota la fecha nueva en el registro (para no volver a bajarlo en la corrida siguiente).
Fuentes: ninguna (no hay acceso a internet: el portal se simula).
Genera: nada (usa una carpeta temporal).

Uso (desde la raíz del repositorio):
    .venv/Scripts/python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import pandas as pd

from comun import descargas  # desde el Paso 3a, scripts/descargas.py reexporta comun/descargas.py
from scripts import secretaria_energia as se

URL_A = "http://datos.energia.gob.ar/dataset/x/resource/11111111-1111-1111-1111-111111111111/download/a.csv"
URL_B = "http://datos.energia.gob.ar/dataset/x/resource/22222222-2222-2222-2222-222222222222/download/b.csv"


class TestPortalSinRespuesta(unittest.TestCase):

    def test_no_baja_y_frena(self):
        with mock.patch.object(se, "metadatos_portal", return_value=None), \
                mock.patch.object(se, "descargar") as descargar:
            with self.assertRaises(se.DescargaFrenada):
                se._bajar_archivo("a.csv", URL_A)
            descargar.assert_not_called()

    def test_revision_lista_los_archivos_sin_verificar_y_el_total(self):
        revision = pd.DataFrame([
            {"archivo": "a.csv", "recurso": "1", "publicacion_registrada": "2026-10-22", "publicacion_portal": None,
             "estado": "sin respuesta", "bytes_registrados": 300_000_000, "bytes_a_bajar": 300_000_000},
            {"archivo": "b.csv", "recurso": "2", "publicacion_registrada": "2026-10-22", "publicacion_portal": "2026-10-22",
             "estado": "sin cambios", "bytes_registrados": 100, "bytes_a_bajar": 100},
        ])
        with self.assertRaises(se.DescargaFrenada) as frenada:
            se.autorizar_descarga(revision, ok_mas_de_1gb=True)  # ni con ok de tamaño se baja a ciegas
        self.assertIn("a.csv", str(frenada.exception))
        self.assertNotIn("b.csv", str(frenada.exception))
        self.assertIn("0.30 GB", str(frenada.exception))


class TestLimiteDeUnGB(unittest.TestCase):
    revision = pd.DataFrame([
        {"archivo": "a.csv", "recurso": "1", "publicacion_registrada": "2026-10-22", "publicacion_portal": "2026-11-22",
         "estado": "cambió", "bytes_registrados": 600_000_000, "bytes_a_bajar": 600_000_000},
        {"archivo": "b.csv", "recurso": "2", "publicacion_registrada": None, "publicacion_portal": "2026-11-22",
         "estado": "nuevo", "bytes_registrados": None, "bytes_a_bajar": 500_000_000},
    ])

    def test_sin_ok_frena(self):
        with self.assertRaises(se.DescargaFrenada):
            se.autorizar_descarga(self.revision)

    def test_con_ok_devuelve_lo_que_hay_que_bajar(self):
        a_bajar = se.autorizar_descarga(self.revision, ok_mas_de_1gb=True)
        self.assertEqual(list(a_bajar["archivo"]), ["a.csv", "b.csv"])

    def test_por_debajo_del_limite_no_pide_ok(self):
        a_bajar = se.autorizar_descarga(self.revision.iloc[:1])
        self.assertEqual(len(a_bajar), 1)


class TestRepublicacionSinCambios(unittest.TestCase):

    def test_anota_la_fecha_nueva_sin_copiar_otra_version(self):
        with tempfile.TemporaryDirectory() as carpeta:
            raiz = Path(carpeta)
            registro_versiones = raiz / "versiones_crudos.csv"
            archivo = raiz / "crudos" / "a.csv"
            archivo.parent.mkdir()
            archivo.write_text("anio,mes\n2026,9\n", encoding="utf-8")
            with mock.patch.object(descargas, "RAIZ", raiz), \
                    mock.patch.object(descargas, "REGISTRO_VERSIONES", registro_versiones):
                registro = descargas._registro(URL_A, archivo, pd.Timestamp("2026-11-18 10:00"), reusado=False)
                primera = descargas.guardar_version(registro, "2026-11-18T10:01:03")
                segunda = descargas.guardar_version(registro, "2026-11-24T10:01:08")
                tercera = descargas.guardar_version(registro, "2026-11-24T10:01:08")
            self.assertTrue(primera["version_nueva"])
            self.assertFalse(segunda["version_nueva"])
            self.assertEqual(primera["version"], segunda["version"])
            self.assertEqual(len(list((archivo.parent / "versiones").iterdir())), 1)
            anotadas = pd.read_csv(registro_versiones)
            self.assertEqual(list(anotadas["fecha_publicacion"]), ["2026-11-18T10:01:03", "2026-11-24T10:01:08"])
            self.assertFalse(tercera["version_nueva"])


if __name__ == "__main__":
    unittest.main()
