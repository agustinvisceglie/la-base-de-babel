"""
Descargas genéricas de archivos públicos, con registro de trazabilidad.

Qué hace:
    - descargar(): baja un archivo de una URL y lo guarda tal cual en datos/crudos/.
      Devuelve un registro con la URL, la ruta local, la fecha y hora de descarga,
      el tamaño y el hash SHA-256 (sirve para saber si el archivo cambió entre corridas).
    - guardar_registro(): escribe en un CSV la lista de descargas de una corrida.

Fuentes: cualquiera. Lo usan los módulos por fuente (api_series_tiempo.py, indec.py, etc.).
Genera: los archivos descargados (en datos/crudos/, que no se sube a GitHub) y el CSV de registro.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

# Carpetas del repositorio (este archivo está en <raiz>/scripts/)
RAIZ = Path(__file__).resolve().parents[1]
CRUDOS = RAIZ / "datos" / "crudos"
PROCESADOS = RAIZ / "datos" / "procesados"

# Encabezado genérico: algunos sitios rechazan pedidos sin "User-Agent".
ENCABEZADOS = {"User-Agent": "Mozilla/5.0 (compatible; descarga-datos-publicos/1.0)"}
ZONA_HORARIA = ZoneInfo("America/Argentina/Buenos_Aires")


def descargar(url: str, destino: Path, reusar_si_existe: bool = False,
              intentos: int = 3, timeout: int = 120) -> dict:
    """Baja `url` a `destino` y devuelve un registro de la descarga.

    - Escribe por partes (streaming), así funciona también con archivos grandes.
    - Si `reusar_si_existe` es True y el archivo ya está, no lo vuelve a bajar
      (útil mientras se desarrolla); en el registro queda la fecha del archivo local.
    """
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)

    if reusar_si_existe and destino.exists():
        fecha = datetime.fromtimestamp(destino.stat().st_mtime, ZONA_HORARIA)
        return _registro(url, destino, fecha, reusado=True)

    ultimo_error = None
    for intento in range(1, intentos + 1):
        try:
            with requests.get(url, headers=ENCABEZADOS, timeout=timeout, stream=True) as respuesta:
                respuesta.raise_for_status()
                temporal = destino.with_suffix(destino.suffix + ".parcial")
                with open(temporal, "wb") as archivo:
                    for bloque in respuesta.iter_content(chunk_size=1024 * 1024):
                        archivo.write(bloque)
                temporal.replace(destino)  # recién al terminar reemplaza al archivo anterior
            return _registro(url, destino, datetime.now(ZONA_HORARIA), reusado=False)
        except requests.RequestException as error:
            ultimo_error = error
            print(f"    intento {intento} de {intentos} fallido para {url}: {error}")

    raise RuntimeError(f"No se pudo descargar {url}. Último error: {ultimo_error}")


def _registro(url: str, destino: Path, fecha: datetime, reusado: bool) -> dict:
    """Arma el registro de una descarga (incluye el hash para detectar cambios)."""
    sha256 = hashlib.sha256()
    with open(destino, "rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            sha256.update(bloque)
    return {
        "archivo": destino.relative_to(RAIZ).as_posix(),
        "url": url,
        "fecha_descarga": fecha.strftime("%Y-%m-%d %H:%M"),
        "bytes": destino.stat().st_size,
        "sha256": sha256.hexdigest(),
        "reusado_de_corrida_anterior": reusado,
    }


def guardar_registro(registros: list[dict], ruta_csv: Path) -> None:
    """Guarda la lista de descargas de una corrida en un CSV."""
    ruta_csv = Path(ruta_csv)
    ruta_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(registros).to_csv(ruta_csv, index=False)
