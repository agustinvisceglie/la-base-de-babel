"""
Registra como versiones los crudos del INDEC, de la base comex y de la API bajados antes del
versionado (Paso 3b del instructivo, 25/11/2026).

Por qué: la nota "La vuelta del gas" bajó esos archivos el 18/11/2026 y anotó la URL, la fecha de
    descarga y el SHA-256 de cada uno en su registro de descargas (commiteado). Los archivos siguen
    en datos/crudos/ con el mismo contenido. Guardarlos como versiones permite reconstruir
    exactamente lo commiteado con actualizar.py --crudos-al 2026-11-18 (la prueba de que la
    migración no cambió ningún número) y conserva la historia.

Qué hace:
    1. Lee los registros de descargas de la nota tal como están en el último commit:
       notas/2026-12-la-vuelta-del-gas/validacion/descargas.csv y descargas_comex.csv.
    2. Para cada archivo: verifica que el SHA-256 del archivo local sea el registrado (si no, frena
       sin registrar nada) y lo guarda como versión comprimida con su nombre lógico (el mismo que
       usan los lectores), la URL, la fecha de descarga y el hash registrados. La fecha de
       publicación queda vacía: no se consultó al bajar.
    No borra ni modifica los archivos originales (las copias "vigentes" se tratan aparte, con ok).

Fuentes: los registros de descargas commiteados de la nota y los archivos de datos/crudos/.
Genera: versiones en datos/crudos/<organismo>/versiones/ y filas en datos/registros/versiones_crudos.csv.

Uso (desde la raíz del repositorio):
    .venv/Scripts/python -m comun.registrar_crudos_previos
"""

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

import pandas as pd

from comun import descargas as d
from lectores import indec

REGISTROS_DE_LA_NOTA = ["notas/2026-12-la-vuelta-del-gas/validacion/descargas.csv",
                        "notas/2026-12-la-vuelta-del-gas/validacion/descargas_comex.csv"]
ORIGEN = ("no informada al bajar: descarga del 18/11/2026, anterior al versionado (mismo SHA-256 que el "
          "registro de descargas commiteado de la nota 'La vuelta del gas')")


def nombre_logico(organismo: str, url: str, archivo: str) -> str:
    """El nombre que usan los lectores: el original, salvo los archivos de la versión interactiva de
    cada informe del ICA, que llevan delante el código del informe (lectores/indec.nombre_local)."""
    if organismo == "indec" and "/ftp/ica_digital/" in url:
        return indec.nombre_local(url)
    return Path(archivo).name


def registrar(commit: str = "HEAD") -> pd.DataFrame:
    filas = []
    for ruta_registro in REGISTROS_DE_LA_NOTA:
        texto = subprocess.run(["git", "show", f"{commit}:{ruta_registro}"], capture_output=True, text=True,
                               encoding="utf-8", cwd=d.RAIZ, check=True).stdout
        filas.append(pd.read_csv(io.StringIO(texto), dtype=str).assign(registro_de_la_nota=ruta_registro))
    anotados = pd.concat(filas).drop_duplicates("archivo", keep="last")

    # Primero se verifica todo; recién después se registra.
    for fila in anotados.itertuples():
        local = d.RAIZ / fila.archivo
        if not local.exists() or d.sha256_de(local) != fila.sha256:
            raise RuntimeError(f"{fila.archivo}: el archivo local no es el registrado por la nota; no se registra nada")

    hechos = []
    for fila in anotados.itertuples():
        organismo = Path(fila.archivo).parts[2]
        logico = f"datos/crudos/{organismo}/{nombre_logico(organismo, fila.url, fila.archivo)}"
        registro = {"archivo": logico, "url": fila.url, "fecha_descarga": fila.fecha_descarga,
                    "bytes": int(fila.bytes), "sha256": fila.sha256}
        resultado = d.guardar_version(registro, None, origen_fecha=ORIGEN, organismo=organismo, origen=d.RAIZ / fila.archivo)
        hechos.append({"archivo_original": fila.archivo, "archivo_logico": logico, "version": resultado["version"],
                       "version_nueva": resultado["version_nueva"], "sha256": fila.sha256})
    return pd.DataFrame(hechos)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    tabla = registrar()
    print(f"{len(tabla)} crudos verificados y registrados como versiones; nuevas: {int(tabla['version_nueva'].sum())}")
    distintos = tabla[tabla["archivo_original"] != tabla["archivo_logico"]]
    if len(distintos):
        print("Con nombre lógico distinto del original:\n" + distintos[["archivo_original", "archivo_logico"]].to_string(index=False))
