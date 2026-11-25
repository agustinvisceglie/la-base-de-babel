"""
Respaldo de las versiones de crudos (.gz) en el OneDrive PERSONAL de Agustín, fuera del repositorio.

Qué hace:
    - Copia cada versión .gz del registro (datos/registros/versiones_crudos.csv) que falte en el
      respaldo, a <respaldo>/<organismo>/<nombre>.gz (la misma estructura que datos/crudos/<organismo>/versiones/).
    - Nunca borra ni pisa nada en el respaldo. Si ya hay un archivo con ese nombre y el mismo tamaño,
      se da por respaldado (con --verificar-todo se recalcula su hash); si tiene otro tamaño o, al
      verificar, otro hash, frena sin tocarlo.
    - Verifica cada copia: el SHA-256 del contenido descomprimido tiene que ser el del registro.
    - Copia también el registro de versiones como versiones_crudos__<12 caracteres del hash>.csv, solo
      si esa versión del registro no estaba (así tampoco se pisa).
    - Anota cada copia en datos/registros/respaldos.csv (fecha, versión, destino relativo a la
      carpeta de respaldo, hash, bytes y resultado).
    - Carpeta de respaldo (aprobada por Agustín el 25/11/2026): <carpeta del usuario>/OneDrive/Respaldos/
      la-base-de-babel/versiones. Se arma desde la carpeta del usuario, así la ruta personal no
      queda escrita en el repositorio público. Se niega a copiar fuera del OneDrive personal (las
      carpetas de OneDrive de empresa se llaman "OneDrive - <organización>" y no se usan).
    No commitea ni hace push.

Fuentes: ninguna (copia lo que ya está en datos/crudos/<organismo>/versiones/).
Genera: las copias en la carpeta de respaldo y filas en datos/registros/respaldos.csv.

Uso (desde la raíz del repositorio):
    .venv/Scripts/python -m comun.respaldar_versiones                   copia lo que falta y lo verifica
    .venv/Scripts/python -m comun.respaldar_versiones --verificar-todo  además recalcula el hash de lo que ya estaba
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from comun import descargas as d

ONEDRIVE_PERSONAL = Path.home() / "OneDrive"
RESPALDO = ONEDRIVE_PERSONAL / "Respaldos" / "la-base-de-babel" / "versiones"
COLUMNAS_RESPALDOS = ["fecha", "version", "destino", "sha256", "bytes", "resultado"]


class RespaldoFrenado(RuntimeError):
    """El respaldo no se hace o se interrumpe sin pisar ni borrar nada."""


def _verificar_destino(destino: Path) -> None:
    destino = destino.resolve()
    raiz = ONEDRIVE_PERSONAL.resolve()
    if not raiz.exists():
        raise RespaldoFrenado(f"No existe la carpeta del OneDrive personal ({raiz.name}): no se respalda.")
    if raiz != destino and raiz not in destino.parents:
        raise RespaldoFrenado("La carpeta de respaldo tiene que estar dentro del OneDrive personal: no se respalda.")


def _hash(ruta: Path) -> str | None:
    """SHA-256 del contenido (descomprimido si es .gz), o None si el archivo está dañado."""
    try:
        return d.sha256_de(ruta)
    except (OSError, EOFError):  # incluye gzip.BadGzipFile
        return None


def _anotar(filas: list[dict], registros: Path) -> None:
    if not filas:
        return
    ruta = registros / "respaldos.csv"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(filas).reindex(columns=COLUMNAS_RESPALDOS).to_csv(ruta, mode="a", header=not ruta.exists(), index=False)


def respaldar(destino: Path = RESPALDO, verificar_todo: bool = False, exigir_onedrive_personal: bool = True,
              registros: Path | None = None) -> pd.DataFrame:
    """Copia al respaldo las versiones que faltan, verifica cada copia y la anota. Devuelve lo hecho."""
    destino = Path(destino)
    registros = Path(registros) if registros else d.RAIZ / "datos" / "registros"
    if exigir_onedrive_personal:
        _verificar_destino(destino)
    registro = d.leer_registro()
    versiones = registro.drop_duplicates("version")[["organismo", "version", "sha256"]]
    hechas, ahora = [], datetime.now().strftime("%Y-%m-%d %H:%M")
    for fila in versiones.itertuples():
        origen = d.RAIZ / fila.version
        if origen.suffix != ".gz":
            raise RespaldoFrenado(f"{fila.version} no está comprimida: se respaldan solo versiones .gz.")
        if not origen.exists():
            raise RespaldoFrenado(f"Falta la versión {fila.version} en el repositorio.")
        copia = destino / fila.organismo / origen.name
        relativo = copia.relative_to(destino).as_posix()
        if copia.exists():
            if copia.stat().st_size != origen.stat().st_size:
                raise RespaldoFrenado(f"En el respaldo ya hay {relativo} con otro tamaño: no se pisa.")
            if verificar_todo and _hash(copia) != fila.sha256:
                raise RespaldoFrenado(f"En el respaldo ya hay {relativo} con otro contenido: no se pisa.")
            continue
        copia.parent.mkdir(parents=True, exist_ok=True)
        temporal = copia.with_name(copia.name[: -len(".gz")] + ".parcial.gz")  # sigue siendo .gz: se verifica descomprimido
        shutil.copy2(origen, temporal)
        if _hash(temporal) != fila.sha256:
            temporal.unlink()
            raise RespaldoFrenado(f"La copia de {fila.version} no reproduce el hash del registro: no se respalda.")
        temporal.replace(copia)
        hechas.append({"fecha": ahora, "version": fila.version, "destino": relativo, "sha256": fila.sha256,
                       "bytes": copia.stat().st_size, "resultado": "copiada y verificada"})

    # Copia del registro de versiones (además está en Git), sin pisar: una por contenido distinto.
    if d.REGISTRO_VERSIONES.exists():
        hash_registro = d.sha256_de(d.REGISTRO_VERSIONES)
        copia = destino / f"versiones_crudos__{hash_registro[:12]}.csv"
        if not copia.exists():
            destino.mkdir(parents=True, exist_ok=True)
            shutil.copy2(d.REGISTRO_VERSIONES, copia)
            if d.sha256_de(copia) != hash_registro:
                raise RespaldoFrenado("La copia del registro de versiones no reproduce su hash.")
            hechas.append({"fecha": ahora, "version": d.REGISTRO_VERSIONES.relative_to(d.RAIZ).as_posix(),
                           "destino": copia.name, "sha256": hash_registro, "bytes": copia.stat().st_size,
                           "resultado": "copiada y verificada"})
    _anotar(hechas, registros)
    return pd.DataFrame(hechas, columns=COLUMNAS_RESPALDOS)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    argumentos = argparse.ArgumentParser(description="Respalda las versiones .gz en el OneDrive personal.")
    argumentos.add_argument("--verificar-todo", action="store_true", help="recalcula el hash de lo que ya estaba en el respaldo")
    tabla = respaldar(verificar_todo=argumentos.parse_args().verificar_todo)
    print(f"Copiadas y verificadas: {len(tabla)} ({tabla['bytes'].sum():,} bytes). No se borró ni se pisó nada.")
