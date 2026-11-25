"""
Tests de comun/descargas.py (versiones comprimidas y descarga condicional por Last-Modified o ETag).

Qué hace: verifica que
    - cada versión se guarde comprimida (.gz), con el hash del original, sin duplicar una versión
      vieja sin comprimir del mismo contenido, y que una republicación solo anote la fecha;
    - la descarga condicional baje solo si cambió el Last-Modified (o el ETag), no deje copia
      "vigente", y frene sin bajar si la fuente no responde;
    - una fuente sin Last-Modified ni ETag (regla 8): si es chica (menos de 50 MB) se baje, se compare
      el hash y, si no cambió, solo se anote; si es grande o no se sabe cuánto pesa, frene sin bajar;
    - los modos sin descargar y crudos al AAAA-MM-DD no usen internet y elijan la versión correcta;
    - el límite de 1 GB frene sin ok y deje pasar con el ok de la corrida.
Fuentes: ninguna (la fuente HTTP se simula; todo pasa en una carpeta temporal).
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

URL = "https://www.indec.gob.ar/ftp/cuadros/economia/prueba.xls"


class BaseTemporal(unittest.TestCase):
    """Cada test corre con la raíz, los crudos y el registro en una carpeta temporal."""

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.raiz = Path(self.carpeta.name)
        self.parches = [mock.patch.object(d, "RAIZ", self.raiz),
                        mock.patch.object(d, "CRUDOS", self.raiz / "datos" / "crudos"),
                        mock.patch.object(d, "REGISTRO_VERSIONES", self.raiz / "datos" / "registros" / "versiones_crudos.csv")]
        for parche in self.parches:
            parche.start()
        d.configurar()
        self.contenido = {"actual": b"anio,valor\n2026,1\n"}

    def tearDown(self):
        d.configurar()
        for parche in self.parches:
            parche.stop()
        self.carpeta.cleanup()

    def bajar_simulado(self, url, destino, **_):
        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(self.contenido["actual"])
        return d._registro(url, destino, pd.Timestamp("2026-11-25 10:00"), reusado=False)

    def registro(self):
        return pd.read_csv(d.REGISTRO_VERSIONES, dtype=str)


class TestVersionesComprimidas(BaseTemporal):

    def test_version_gz_con_hash_del_original(self):
        archivo = self.raiz / "datos" / "crudos" / "indec" / "a.csv"
        archivo.parent.mkdir(parents=True)
        archivo.write_bytes(b"x,y\n1,2\n")
        registro = d._registro(URL, archivo, pd.Timestamp("2026-11-25 10:00"), reusado=False)
        resultado = d.guardar_version(registro, "2026-11-19T18:51:19+00:00")
        version = self.raiz / resultado["version"]
        self.assertTrue(version.name.endswith(".csv.gz"))
        self.assertEqual(d.sha256_de(version), registro["sha256"])
        self.assertEqual(d.leer_bytes(version).read(), b"x,y\n1,2\n")
        fila = self.registro().iloc[0]
        self.assertEqual(fila["organismo"], "indec")
        self.assertEqual(fila["sha256"], registro["sha256"])

    def test_no_duplica_una_version_vieja_sin_comprimir(self):
        archivo = self.raiz / "datos" / "crudos" / "secretaria_energia" / "b.csv"
        (archivo.parent / "versiones").mkdir(parents=True)
        archivo.write_bytes(b"z\n3\n")
        registro = d._registro(URL, archivo, pd.Timestamp("2026-11-25 10:00"), reusado=False)
        vieja = archivo.parent / "versiones" / f"b__2026-10-22__{registro['sha256'][:12]}.csv"
        vieja.write_bytes(b"z\n3\n")
        resultado = d.guardar_version(registro, "2026-11-22T21:00:55")
        self.assertFalse(resultado["version_nueva"])
        self.assertEqual(Path(resultado["version"]).name, vieja.name)
        self.assertEqual(len(list((archivo.parent / "versiones").iterdir())), 1)

    def test_republicacion_solo_anota_la_fecha(self):
        archivo = self.raiz / "datos" / "crudos" / "indec" / "c.csv"
        archivo.parent.mkdir(parents=True)
        archivo.write_bytes(b"w\n4\n")
        registro = d._registro(URL, archivo, pd.Timestamp("2026-11-25 10:00"), reusado=False)
        d.guardar_version(registro, "2026-11-18T10:00:00")
        d.guardar_version(registro, "2026-11-24T10:00:00")
        d.guardar_version(registro, "2026-11-24T10:00:00")
        self.assertEqual(list(self.registro()["fecha_publicacion"]), ["2026-11-18T10:00:00", "2026-11-24T10:00:00"])
        self.assertEqual(len(list((archivo.parent / "versiones").iterdir())), 1)


class TestDescargaCondicional(BaseTemporal):

    def correr(self, metadatos):
        with mock.patch.object(d, "metadatos_http", return_value=metadatos), \
                mock.patch.object(d, "descargar", side_effect=self.bajar_simulado) as bajar:
            resultado = d.descargar_condicional(URL, "indec", "prueba.xls")
        return resultado, bajar

    def test_baja_la_primera_vez_y_no_deja_copia_vigente(self):
        resultado, bajar = self.correr({"fecha_publicacion": "2026-11-19T18:51:19+00:00", "etag": '"abc"', "bytes": 18})
        self.assertEqual(bajar.call_count, 1)
        self.assertTrue(resultado["descargado"])
        crudos = self.raiz / "datos" / "crudos" / "indec"
        self.assertEqual([p.name for p in crudos.iterdir() if p.is_file()], [])  # solo queda versiones/
        self.assertEqual(self.registro().iloc[0]["origen_fecha"], "encabezado Last-Modified")

    def test_mismo_last_modified_no_baja(self):
        metadatos = {"fecha_publicacion": "2026-11-19T18:51:19+00:00", "etag": '"abc"', "bytes": 18}
        self.correr(metadatos)
        resultado, bajar = self.correr(metadatos)
        self.assertEqual(bajar.call_count, 0)
        self.assertFalse(resultado["descargado"])

    def test_last_modified_nuevo_baja_y_guarda_otra_version(self):
        self.correr({"fecha_publicacion": "2026-11-19T18:51:19+00:00", "etag": '"abc"', "bytes": 18})
        self.contenido["actual"] = b"anio,valor\n2026,2\n"
        resultado, bajar = self.correr({"fecha_publicacion": "2026-12-17T18:00:00+00:00", "etag": '"def"', "bytes": 18})
        self.assertEqual(bajar.call_count, 1)
        self.assertTrue(resultado["version_nueva"])
        self.assertEqual(len(self.registro()), 2)

    def test_solo_etag_igual_no_baja(self):
        self.correr({"fecha_publicacion": None, "etag": 'W/"1"', "bytes": 18})
        resultado, bajar = self.correr({"fecha_publicacion": None, "etag": 'W/"1"', "bytes": 18})
        self.assertEqual(bajar.call_count, 0)

    def test_sin_fecha_grande_frena_sin_bajar(self):
        with mock.patch.object(d, "metadatos_http", return_value={"fecha_publicacion": None, "etag": None, "bytes": 60_000_000}), \
                mock.patch.object(d, "descargar") as bajar:
            with self.assertRaises(d.DescargaFrenada):
                d.descargar_condicional(URL, "indec", "prueba.xls")
            bajar.assert_not_called()

    def test_sin_fecha_y_sin_tamanio_conocido_frena_sin_bajar(self):
        with mock.patch.object(d, "metadatos_http", return_value={"fecha_publicacion": None, "etag": None, "bytes": None}), \
                mock.patch.object(d, "descargar") as bajar:
            with self.assertRaises(d.DescargaFrenada):
                d.descargar_condicional(URL, "indec", "prueba.xls")
            bajar.assert_not_called()

    def test_sin_fecha_chica_baja_compara_el_hash_y_anota(self):
        sin_fecha = {"fecha_publicacion": None, "etag": None, "bytes": 18}
        primera, _ = self.correr(sin_fecha)                       # versión nueva, con la fecha de descarga
        segunda, bajar = self.correr(sin_fecha)                   # mismo contenido: solo se anota
        self.assertEqual(bajar.call_count, 1)
        self.assertTrue(primera["version_nueva"])
        self.assertFalse(segunda["version_nueva"])
        self.assertEqual(primera["version"], segunda["version"])
        self.contenido["actual"] = b"anio,valor\n2026,7\n"
        tercera, _ = self.correr(sin_fecha)                       # cambió: versión nueva
        self.assertTrue(tercera["version_nueva"])
        registro = self.registro()
        self.assertEqual(list(registro["origen_fecha"]), [d.ORIGEN_SIN_FECHA, d.ORIGEN_SIN_FECHA_SIN_CAMBIOS, d.ORIGEN_SIN_FECHA])
        self.assertTrue(registro["fecha_publicacion"].isna().all())
        self.assertEqual(len(list((self.raiz / "datos" / "crudos" / "indec" / "versiones").iterdir())), 2)

    def test_sin_fecha_ni_tamanio_de_la_fuente_usa_el_de_la_ultima_version(self):
        self.correr({"fecha_publicacion": None, "etag": None, "bytes": 18})
        resultado, bajar = self.correr({"fecha_publicacion": None, "etag": None, "bytes": None})
        self.assertEqual(bajar.call_count, 1)  # la última versión pesa 18 bytes: es chica
        self.assertFalse(resultado["version_nueva"])

    def test_fuente_sin_respuesta_frena_sin_bajar(self):
        with mock.patch.object(d, "metadatos_http", return_value=None), mock.patch.object(d, "descargar") as bajar:
            with self.assertRaises(d.DescargaFrenada):
                d.descargar_condicional(URL, "indec", "prueba.xls")
            bajar.assert_not_called()

    def test_sin_descargar_y_crudos_al_no_usan_internet(self):
        self.correr({"fecha_publicacion": "2026-10-20T10:00:00+00:00", "etag": '"a"', "bytes": 18})
        self.contenido["actual"] = b"anio,valor\n2026,9\n"
        self.correr({"fecha_publicacion": "2026-11-19T10:00:00+00:00", "etag": '"b"', "bytes": 18})
        with mock.patch.object(d, "metadatos_http") as encabezados, mock.patch.object(d, "descargar") as bajar:
            d.configurar(sin_descargar=True)
            ultima = d.descargar_condicional(URL, "indec", "prueba.xls")
            d.configurar(crudos_al="2026-10-31")
            al_31_10 = d.descargar_condicional(URL, "indec", "prueba.xls")
            d.configurar(crudos_al="2026-09-30")
            with self.assertRaises(d.DescargaFrenada):
                d.descargar_condicional(URL, "indec", "prueba.xls")
            encabezados.assert_not_called()
            bajar.assert_not_called()
        self.assertEqual(d.leer_bytes(ultima["version"]).read(), b"anio,valor\n2026,9\n")
        self.assertEqual(d.leer_bytes(al_31_10["version"]).read(), b"anio,valor\n2026,1\n")


class TestLimiteDeUnGB(BaseTemporal):
    revision = pd.DataFrame([{"archivo": "a", "estado": "cambió", "publicacion_registrada": None,
                              "publicacion_fuente": "x", "bytes_a_bajar": 1_200_000_000}])

    def test_sin_ok_frena(self):
        with self.assertRaises(d.DescargaFrenada):
            d.autorizar_descarga(self.revision)

    def test_con_el_ok_de_la_corrida_pasa(self):
        d.configurar(ok_mas_de_1gb=True)
        self.assertEqual(len(d.autorizar_descarga(self.revision)), 1)

    def test_sin_fecha_grande_frena_aunque_haya_ok(self):
        d.configurar(ok_mas_de_1gb=True)
        revision = self.revision.assign(estado="sin fecha, grande o sin tamaño")
        with self.assertRaises(d.DescargaFrenada):
            d.autorizar_descarga(revision)

    def test_sin_fecha_chica_se_baja(self):
        revision = self.revision.assign(estado="sin fecha, chica", bytes_a_bajar=2_272)
        self.assertEqual(len(d.autorizar_descarga(revision)), 1)


if __name__ == "__main__":
    unittest.main()
