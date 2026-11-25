"""
Tests del catálogo (comun/catalogo.py), de los controles bloqueantes (comun/controles.py) y de actualizar.py.

Qué hace: verifica que
    - en el repositorio, toda columna de serie de datos/series/ tenga su fila en catalogo_series.csv
      y toda fila del catálogo apunte a una columna que existe (los dos sentidos);
    - el catálogo tenga las columnas acordadas (incluidas uso, rotulo, inicio, discontinuada y
      con_reservas) y el rótulo solo acepte los valores aprobados;
    - una declaración de series incompleta o con valores inválidos se rechace;
    - las dependencias entre armadores se resuelvan en orden y un ciclo frene;
    - actualizar.py escriba las series y el catálogo cuando los controles dan bien; no escriba nada
      si un control da REVISAR sin excepción aprobada (y no corra lo que depende de ese armador);
      escriba si la excepción está aprobada, pero no si solo está propuesta; y registre la corrida;
    - ni actualizar.py ni comun/ commiteen (no llaman a git).
Fuentes: ninguna (armadores y carpetas de prueba).
Genera: nada.

Uso (desde la raíz del repositorio):
    .venv/Scripts/python -m unittest discover -s tests -v
"""

import sys
import tempfile
import types
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import pandas as pd

import actualizar
from comun import catalogo
from comun.controles import COLUMNAS_EXCEPCIONES


def declaracion(archivo, columna, **cambios):
    serie = {"archivo": archivo, "columna": columna, "nombre": f"Serie {columna}", "unidad": "millones de USD",
             "frecuencia": "mensual", "tipo": "nivel", "precios": "corrientes", "ajuste_estacional": "original",
             "uso": "base", "organismo": "INDEC", "rotulo": "oficial", "fuente_id": "cuadro 1", "fuente_url": "https://www.indec.gob.ar",
             "lector": "lectores/indec.py", "criterio": "§1", "estimados": "no", "tiene_revisiones": "sí",
             "discontinuada": "no", "con_reservas": "no", "informe_validacion": "datos/validacion/x/informe.md"}
    serie.update(cambios)
    return serie


def armador_de_prueba(bloque, nombre, series, tablas, controles, depende_de=(), auxiliares=None):
    modulo = types.ModuleType(f"bloques.{bloque}.{nombre}")
    modulo.SERIES = series
    modulo.DEPENDE_DE = list(depende_de)
    modulo.AUXILIARES = auxiliares or {}
    modulo.armar = lambda: {"series": tablas, "controles": pd.DataFrame(controles),
                            "registros": [{"fecha_publicacion": "2026-11-19T18:51:19", "sha256": "abcdef1234567890"}]}
    return catalogo.desde_modulo(modulo, bloque, nombre, f"bloques/{bloque}/{nombre}.py")


def tabla_mensual(**columnas):
    fechas = pd.date_range("2026-01-01", periods=3, freq="MS", name="fecha")
    return pd.DataFrame(columnas, index=fechas)


class TestCatalogoDelRepositorio(unittest.TestCase):
    """El test permanente de los dos sentidos, sobre el repositorio real."""

    def test_toda_serie_tiene_su_fila_y_viceversa(self):
        lista = catalogo.armadores(RAIZ)
        faltan, sobran = catalogo.verificar_catalogo(catalogo.leer_catalogo(RAIZ), lista, RAIZ)
        self.assertEqual(faltan, [], "columnas de datos/series/ sin fila en el catálogo")
        self.assertEqual(sobran, [], "filas del catálogo que no apuntan a una columna existente")

    def test_columnas_del_catalogo(self):
        columnas = list(pd.read_csv(RAIZ / "catalogo_series.csv", nrows=0).columns)
        self.assertEqual(columnas, catalogo.COLUMNAS_CATALOGO)
        for columna in ("uso", "rotulo", "inicio", "discontinuada", "con_reservas"):
            self.assertIn(columna, columnas)

    def test_valores_del_rotulo(self):
        self.assertEqual(catalogo.VALORES_VALIDOS["rotulo"],
                         {"oficial", "no oficial", "no oficial (académica)", "regulado", "estimación propia"})

    def test_columnas_de_excepciones(self):
        columnas = list(pd.read_csv(RAIZ / "datos" / "registros" / "excepciones.csv", nrows=0).columns)
        self.assertEqual(columnas, COLUMNAS_EXCEPCIONES)


class TestDeclaracionesYDependencias(unittest.TestCase):

    def test_declaracion_invalida_se_rechaza(self):
        with self.assertRaises(ValueError):
            armador_de_prueba("energia", "a", [declaracion("a.csv", "x", uso="principal")], {}, [])
        with self.assertRaises(ValueError):
            armador_de_prueba("energia", "a", [declaracion("a.csv", "x", rotulo="privado")], {}, [])
        incompleta = declaracion("a.csv", "x")
        del incompleta["unidad"]
        with self.assertRaises(ValueError):
            armador_de_prueba("energia", "a", [incompleta], {}, [])

    def test_orden_por_dependencias_y_ciclo(self):
        base = armador_de_prueba("sector_externo", "comex", [declaracion("comex.csv", "cye")], {}, [])
        derivado = armador_de_prueba("energia", "balanza", [declaracion("balanza.csv", "saldo")], {}, [],
                                     depende_de=["sector_externo.comex.cye"])
        orden = catalogo.resolver([derivado, base], bloque="energia")
        self.assertEqual([a.nombre for a in orden], ["comex", "balanza"])
        ciclo_a = armador_de_prueba("energia", "a", [declaracion("a.csv", "x")], {}, [], depende_de=["energia.b.y"])
        ciclo_b = armador_de_prueba("energia", "b", [declaracion("b.csv", "y")], {}, [], depende_de=["energia.a.x"])
        with self.assertRaises(ValueError):
            catalogo.resolver([ciclo_a, ciclo_b])


class TestActualizar(unittest.TestCase):

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.raiz = Path(self.carpeta.name)
        (self.raiz / "datos" / "registros").mkdir(parents=True)
        pd.DataFrame(columns=COLUMNAS_EXCEPCIONES).to_csv(self.raiz / "datos" / "registros" / "excepciones.csv", index=False)

    def tearDown(self):
        self.carpeta.cleanup()

    def armadores(self, estado):
        comex = armador_de_prueba("sector_externo", "comex", [declaracion("comex.csv", "cye")],
                                  {"comex.csv": tabla_mensual(cye=[1.0, 2.0, 3.0], dias_del_mes=[31, 28, 31])},
                                  [{"control": "Total = suma de rubros", "estado": estado, "detalle": "", "alcance": "2026-02"}],
                                  auxiliares={"comex.csv": ["dias_del_mes"]})
        balanza = armador_de_prueba("energia", "balanza", [declaracion("balanza.csv", "saldo", tipo="saldo")],
                                    {"balanza.csv": tabla_mensual(saldo=[0.5, None, 1.5])},
                                    [{"control": "Saldo = CyE - CyL", "estado": "OK", "detalle": ""}],
                                    depende_de=["sector_externo.comex.cye"])
        return [comex, balanza]

    def corridas(self):
        return pd.read_csv(self.raiz / "datos" / "registros" / "corridas.csv")

    def test_controles_ok_escribe_series_y_catalogo(self):
        salida = actualizar.ejecutar([], lista=self.armadores("OK"), raiz=self.raiz)
        self.assertEqual(salida, 0)
        self.assertTrue((self.raiz / "datos" / "series" / "energia" / "balanza.csv").exists())
        cat = pd.read_csv(self.raiz / "catalogo_series.csv", dtype=str)
        self.assertEqual(sorted(cat["id"]), ["energia.balanza.saldo", "sector_externo.comex.cye"])
        fila = cat.set_index("id").loc["energia.balanza.saldo"]
        self.assertEqual((fila["inicio"], fila["fin"]), ("2026-01-01", "2026-03-01"))
        self.assertEqual(fila["version_crudo"], "abcdef123456")
        self.assertEqual(fila["estado_validacion"], "controles OK")
        self.assertEqual(self.corridas().iloc[-1]["resultado"], "ok")

    def test_revisar_sin_excepcion_no_escribe_nada(self):
        salida = actualizar.ejecutar([], lista=self.armadores("REVISAR"), raiz=self.raiz)
        self.assertEqual(salida, 1)
        self.assertFalse((self.raiz / "datos" / "series" / "sector_externo" / "comex.csv").exists())
        self.assertFalse((self.raiz / "datos" / "series" / "energia" / "balanza.csv").exists())  # depende del frenado
        self.assertEqual(self.corridas().iloc[-1]["resultado"], "error")

    def test_excepcion_aprobada_deja_escribir_y_propuesta_no(self):
        excepcion = {"id": "1", "bloque": "sector_externo", "control": "Total = suma de rubros", "alcance": "2026-02",
                     "motivo": "prueba", "evidencia": "test", "estado": "propuesta", "fecha_propuesta": "2026-11-25",
                     "fecha_auditoria": "", "auditoria": ""}
        ruta = self.raiz / "datos" / "registros" / "excepciones.csv"
        pd.DataFrame([excepcion]).to_csv(ruta, index=False)
        self.assertEqual(actualizar.ejecutar([], lista=self.armadores("REVISAR"), raiz=self.raiz), 1)
        pd.DataFrame([{**excepcion, "estado": "aprobada"}]).to_csv(ruta, index=False)
        self.assertEqual(actualizar.ejecutar([], lista=self.armadores("REVISAR"), raiz=self.raiz), 0)
        self.assertTrue((self.raiz / "datos" / "series" / "sector_externo" / "comex.csv").exists())

    def test_nunca_commitea(self):
        for ruta in [RAIZ / "actualizar.py", *sorted((RAIZ / "comun").glob("*.py"))]:
            texto = ruta.read_text(encoding="utf-8")
            self.assertNotIn("subprocess", texto, ruta.name)
            self.assertNotIn("git commit", texto, ruta.name)
            self.assertNotIn("git push", texto, ruta.name)


if __name__ == "__main__":
    unittest.main()
