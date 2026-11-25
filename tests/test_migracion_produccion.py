"""
Test de la migración de producción (Paso 3c): con los crudos que había el 25/11/2026 a las 10:59, la
base reproduce exactamente lo commiteado antes de migrar (commit 19f26b0, el Paso 1).

Qué hace:
    1. Arma el bloque de producción (bloques/energia/produccion.py) con
       actualizar.py --crudos-al "2026-11-25 10:59" en una carpeta temporal (sin internet: usa las
       versiones guardadas). Tarda alrededor de un minuto: lee los 17 DDJJ comprimidos.
    2. Compara, texto contra texto, la serie nacional y la de Vaca Muerta (antes en datos/procesados/,
       ahora en datos/series/energia/) con lo commiteado en 19f26b0.
    3. Hace lo mismo con las tablas de validación que respaldan Vaca Muerta: DDJJ contra serie mes
       por mes, reclasificaciones y Vaca Muerta con los DDJJ contra el archivo no convencional.
    Si faltan las versiones guardadas (por ejemplo, en otra PC) o git no tiene ese commit, el test
    se saltea: no se puede reproducir sin los crudos.
Fuentes: versiones en datos/crudos/secretaria_energia/versiones/ y el historial de git.
Genera: nada (usa una carpeta temporal).

Uso (desde la raíz del repositorio):
    .venv/Scripts/python -m unittest discover -s tests -v
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import actualizar
from comun import catalogo, descargas

COMMIT_ANTES = "19f26b0"
CRUDOS_AL = "2026-11-25 10:59"
ARMADOR = "bloques/energia/produccion.py"


def commiteado(ruta: str) -> str | None:
    resultado = subprocess.run(["git", "show", f"{COMMIT_ANTES}:{ruta}"], capture_output=True, text=True, encoding="utf-8", cwd=RAIZ)
    return resultado.stdout if resultado.returncode == 0 else None


class TestMigracionProduccion(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if commiteado("datos/procesados/produccion_vaca_muerta_mensual.csv") is None:
            raise unittest.SkipTest(f"git no tiene el commit {COMMIT_ANTES}")
        try:
            descargas.version_registrada("datos/crudos/secretaria_energia/produccion_pozos_2026_ddjj_abiertas_cerradas.csv", CRUDOS_AL)
        except descargas.DescargaFrenada:
            raise unittest.SkipTest("faltan las versiones de los crudos de la SE del 25/11/2026")
        cls.carpeta = tempfile.TemporaryDirectory()
        cls.raiz = Path(cls.carpeta.name)
        (cls.raiz / "datos" / "registros").mkdir(parents=True)
        lista = [a for a in catalogo.armadores(RAIZ) if a.ruta == ARMADOR]
        cls.salida = actualizar.ejecutar(["--crudos-al", CRUDOS_AL], lista=lista, raiz=cls.raiz)

    @classmethod
    def tearDownClass(cls):
        descargas.configurar()
        catalogo.usar_raiz(RAIZ)
        cls.carpeta.cleanup()

    def comparar(self, antes: str, ahora: Path):
        esperado = commiteado(antes).replace("\r\n", "\n")
        obtenido = ahora.read_text(encoding="utf-8").replace("\r\n", "\n")
        if esperado != obtenido:
            distintas = [(a, b) for a, b in zip(esperado.splitlines(), obtenido.splitlines()) if a != b][:3]
            self.fail(f"{antes} cambió: {len(esperado.splitlines())} vs {len(obtenido.splitlines())} líneas; primeras distintas: {distintas}")

    def test_corre_sin_frenos(self):
        self.assertEqual(self.salida, 0)

    def test_serie_nacional_identica(self):
        self.comparar("datos/procesados/produccion_petroleo_gas_mensual.csv",
                      self.raiz / "datos" / "series" / "energia" / "produccion_petroleo_gas_mensual.csv")

    def test_vaca_muerta_identica(self):
        self.comparar("datos/procesados/produccion_vaca_muerta_mensual.csv",
                      self.raiz / "datos" / "series" / "energia" / "produccion_vaca_muerta_mensual.csv")

    def test_validacion_de_vaca_muerta_identica(self):
        for archivo in ("produccion_ddjj_vs_serie.csv", "produccion_reclasificaciones.csv",
                        "produccion_vaca_muerta_ddjj_vs_no_convencional.csv", "produccion_vs_primera_difusion.csv"):
            with self.subTest(archivo=archivo):
                self.comparar(f"datos/validacion/{archivo}", self.raiz / "datos" / "validacion" / "energia" / archivo)


if __name__ == "__main__":
    unittest.main()
