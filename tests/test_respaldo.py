"""
Tests del respaldo de versiones (comun/respaldar_versiones.py).

Qué hace: verifica que el respaldo
    - copie solo las versiones .gz que faltan, verifique el hash de cada copia contra el registro y
      lo anote en datos/registros/respaldos.csv; una segunda corrida no copia nada;
    - nunca pise un archivo del respaldo con el mismo nombre (otro tamaño u otro contenido): frena;
    - se niegue a copiar fuera del OneDrive personal.
Fuentes: ninguna (todo pasa en una carpeta temporal; el OneDrive se simula).
Genera: nada.

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

from comun import descargas as d
from comun import respaldar_versiones as r

URL = "https://www.indec.gob.ar/ftp/cuadros/economia/prueba.csv"


class TestRespaldo(unittest.TestCase):

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.raiz = Path(self.carpeta.name) / "repo"
        self.onedrive = Path(self.carpeta.name) / "OneDrive"
        self.destino = self.onedrive / "Respaldos" / "la-base-de-babel" / "versiones"
        self.onedrive.mkdir(parents=True)
        self.parches = [mock.patch.object(d, "RAIZ", self.raiz), mock.patch.object(d, "CRUDOS", self.raiz / "datos" / "crudos"),
                        mock.patch.object(d, "REGISTRO_VERSIONES", self.raiz / "datos" / "registros" / "versiones_crudos.csv"),
                        mock.patch.object(r, "ONEDRIVE_PERSONAL", self.onedrive)]
        for parche in self.parches:
            parche.start()
        for nombre, contenido in (("a.csv", b"x,y\n1,2\n"), ("b.csv", b"z\n3\n")):
            archivo = self.raiz / "datos" / "crudos" / "indec" / nombre
            archivo.parent.mkdir(parents=True, exist_ok=True)
            archivo.write_bytes(contenido)
            d.guardar_version(d._registro(URL, archivo, pd.Timestamp("2026-11-25 10:00"), reusado=False), "2026-11-19T18:51:19")

    def tearDown(self):
        for parche in self.parches:
            parche.stop()
        self.carpeta.cleanup()

    def respaldar(self, **opciones):
        return r.respaldar(destino=self.destino, registros=self.raiz / "datos" / "registros", **opciones)

    def test_copia_lo_que_falta_verifica_y_anota(self):
        primera = self.respaldar()
        self.assertEqual(len(primera), 3)  # 2 versiones + la copia del registro de versiones
        copias = sorted(p.name for p in (self.destino / "indec").iterdir())
        self.assertEqual(len(copias), 2)
        for copia in (self.destino / "indec").iterdir():
            self.assertIn(d.sha256_de(copia), set(d.leer_registro()["sha256"]))
        anotadas = pd.read_csv(self.raiz / "datos" / "registros" / "respaldos.csv")
        self.assertEqual(list(anotadas["resultado"].unique()), ["copiada y verificada"])
        self.assertEqual(len(self.respaldar()), 0)  # segunda corrida: no copia nada

    def test_no_pisa_un_archivo_distinto(self):
        self.respaldar()
        copia = next((self.destino / "indec").iterdir())
        copia.write_bytes(b"otro contenido de otro largo")
        with self.assertRaises(r.RespaldoFrenado):
            self.respaldar()
        self.assertEqual(copia.read_bytes(), b"otro contenido de otro largo")

    def test_verificar_todo_detecta_mismo_largo_y_otro_contenido(self):
        self.respaldar()
        copia = next((self.destino / "indec").iterdir())
        largo = copia.stat().st_size
        copia.write_bytes(b"\0" * largo)
        self.assertEqual(len(self.respaldar()), 0)  # sin verificar todo, el tamaño coincide y no se toca
        with self.assertRaises(r.RespaldoFrenado):
            self.respaldar(verificar_todo=True)

    def test_se_niega_fuera_del_onedrive_personal(self):
        afuera = Path(self.carpeta.name) / "OneDrive - Empresa" / "Respaldos"
        with self.assertRaises(r.RespaldoFrenado):
            r.respaldar(destino=afuera, registros=self.raiz / "datos" / "registros")
        self.assertFalse(afuera.exists())


if __name__ == "__main__":
    unittest.main()
