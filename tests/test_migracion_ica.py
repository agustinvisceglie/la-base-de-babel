"""
Test de la migración del comercio exterior (Paso 3b): con los crudos que había el 18/11/2026, la base
reproduce exactamente lo commiteado antes de migrar (commit b0909cd).

Qué hace:
    1. Arma los bloques de sector externo y de energía con actualizar.py --crudos-al 2026-11-18 en
       una carpeta temporal (sin internet: usa las versiones guardadas).
    2. Compara cada número de ica_mensual, ica_anual e ica_cap27_mensual (antes en datos/procesados/;
       ahora en datos/series/sector_externo/ y, el saldo CyE - CyL, en datos/series/energia/) con lo
       commiteado en b0909cd, con la precisión con que se publicó (3 decimales).
    3. Arma g1, g2 y las cifras de la nota "La vuelta del gas" leyendo esa base y las compara, texto
       contra texto, con lo commiteado en b0909cd.
    Si faltan las versiones guardadas (por ejemplo, en otra PC) o git no tiene ese commit, el test
    se saltea: no se puede reproducir sin los crudos.
Fuentes: versiones en datos/crudos/*/versiones/ y el historial de git.
Genera: nada (usa una carpeta temporal).

Uso (desde la raíz del repositorio):
    .venv/Scripts/python -m unittest discover -s tests -v
"""

import importlib.util
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import pandas as pd

import actualizar
from comun import catalogo, descargas

COMMIT_ANTES = "b0909cd"
NOTA = "notas/2026-12-la-vuelta-del-gas"
ARMADORES = ["bloques/sector_externo/comercio_exterior.py", "bloques/energia/balanza_energetica.py"]


def commiteado(ruta: str) -> str | None:
    resultado = subprocess.run(["git", "show", f"{COMMIT_ANTES}:{ruta}"], capture_output=True, text=True, encoding="utf-8", cwd=RAIZ)
    return resultado.stdout if resultado.returncode == 0 else None


def cargar_nota():
    especificacion = importlib.util.spec_from_file_location("nota_vuelta_del_gas", RAIZ / NOTA / "1_ica.py")
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


class TestMigracionComercioExterior(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if commiteado("datos/procesados/ica_mensual.csv") is None:
            raise unittest.SkipTest(f"git no tiene el commit {COMMIT_ANTES}")
        try:
            descargas.version_registrada("datos/crudos/indec/ica_cuadros_19_10_26.xls", "2026-11-18")
        except descargas.DescargaFrenada:
            raise unittest.SkipTest("faltan las versiones de los crudos del 18/11/2026")
        cls.carpeta = tempfile.TemporaryDirectory()
        cls.raiz = Path(cls.carpeta.name)
        (cls.raiz / "datos" / "registros").mkdir(parents=True)
        lista = [a for a in catalogo.armadores(RAIZ) if a.ruta in ARMADORES]
        cls.salida = actualizar.ejecutar(["--crudos-al", "2026-11-18"], lista=lista, raiz=cls.raiz)

    @classmethod
    def tearDownClass(cls):
        descargas.configurar()
        catalogo.usar_raiz(RAIZ)
        cls.carpeta.cleanup()

    def series(self, *archivos):
        tabla = None
        for archivo in archivos:
            t = pd.read_csv(self.raiz / "datos" / "series" / archivo, index_col=0)
            tabla = t if tabla is None else tabla.join(t, rsuffix="_otra")
        tabla.index = tabla.index.astype(str)
        return tabla

    def comparar(self, viejo_ruta, *nuevos):
        viejo = pd.read_csv(io.StringIO(commiteado(viejo_ruta)), dtype=str, keep_default_na=False, index_col=0)
        nuevo = self.series(*nuevos)
        self.assertEqual(list(viejo.index), list(nuevo.index), viejo_ruta)
        for columna in viejo.columns:
            valores = nuevo[columna].reindex(viejo.index)
            texto = valores.map(lambda v: "" if pd.isna(v) else ("%.3f" % v if isinstance(v, float) else str(v)))
            distintos = texto != viejo[columna]
            self.assertFalse(distintos.any(), f"{viejo_ruta}, {columna}: {list(zip(viejo[columna][distintos], texto[distintos]))[:3]}")

    def test_corre_sin_frenos(self):
        self.assertEqual(self.salida, 0)

    def test_ica_mensual_identico(self):
        self.comparar("datos/procesados/ica_mensual.csv", "sector_externo/ica_mensual.csv", "energia/balanza_energetica_mensual.csv")

    def test_ica_anual_identico(self):
        self.comparar("datos/procesados/ica_anual.csv", "sector_externo/ica_anual.csv", "energia/balanza_energetica_anual.csv")

    def test_cap27_mensual_identico(self):
        self.comparar("datos/procesados/ica_cap27_mensual.csv", "sector_externo/ica_cap27_mensual.csv")

    def test_g1_g2_y_cifras_de_la_nota_identicos(self):
        nota = cargar_nota()
        catalogo.usar_raiz(self.raiz)
        base = nota.leer_base()
        salidas = {
            "graficos/g1_balanza_energetica_anual.csv": nota.armar_g1(base["anual"], base["corte"]).to_csv(float_format="%.1f"),
            "graficos/g2_saldo_energetico_vs_total_12m.csv": nota.armar_g2(base["ica"]).to_csv(float_format="%.1f", date_format="%Y-%m-%d"),
            "cifras_para_el_texto.csv": nota.armar_cifras_para_el_texto(base["anual"], base["corte"]).to_csv(float_format="%.1f"),
        }
        for archivo, texto in salidas.items():
            esperado = commiteado(f"{NOTA}/{archivo}")
            self.assertEqual(texto.replace("\r\n", "\n"), esperado.replace("\r\n", "\n"), archivo)


if __name__ == "__main__":
    unittest.main()
