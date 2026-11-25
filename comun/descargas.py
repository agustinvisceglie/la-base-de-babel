"""
Descargas y versiones de los crudos (código común, sin criterios económicos).

Qué hace:
    - descargar(): baja un archivo de una URL, por partes, y devuelve un registro con la URL, la
      ruta, la fecha de descarga, los bytes y el SHA-256.
    - guardar_version(): guarda cada versión distinta de un crudo **comprimida** en
      datos/crudos/<organismo>/versiones/<nombre>__<fecha de publicación>__<12 caracteres del hash>.<ext>.gz.
      El hash se calcula sobre el archivo original, sin comprimir (y se verifica al descomprimir).
      Nunca pisa ni borra una versión. Las versiones viejas sin comprimir (anteriores al Paso 3a)
      se reconocen por el hash y no se duplican. Anota cada versión, y cada republicación del mismo
      contenido con otra fecha, en datos/registros/versiones_crudos.csv (solo agrega filas).
    - metadatos_http(): pide solo los encabezados (HEAD): Last-Modified, ETag y tamaño.
    - descargar_condicional(): para fuentes que publican por HTTP (INDEC, BCRA, ...): baja solo si el
      Last-Modified o el ETag cambiaron respecto de la última versión registrada. No deja una copia
      "vigente": solo la versión comprimida. Si la fuente no informa ninguno de los dos (regla 8 del
      instructivo, precisada el 25/11/2026): si pesa menos de 50 MB, se baja, se compara el hash y,
      si ya estaba, solo se anota la verificación; si cambió, se guarda con la fecha de descarga
      (origen_fecha lo dice). Si es grande o no se sabe cuánto pesa, frena sin bajar.
    - revisar_http() y autorizar_descarga(): antes de bajar, qué cambió y cuánto pesa; frenan si la
      fuente no responde, si no informa fecha ni ETag y es grande o de tamaño desconocido, o si lo
      que hay que bajar pasa 1 GB sin el ok de Agustín (regla 8).
    - configurar(): los modos de actualizar.py: sin descargar (usa las últimas versiones bajadas) y
      crudos al AAAA-MM-DD (usa, de cada crudo, la última versión bajada hasta esa fecha: lo que
      teníamos ese día, según la fecha de descarga del registro).
    - version_registrada() y leer_bytes(): ubican la versión que corresponde y la abren (comprimida o no).

Columnas de datos/registros/versiones_crudos.csv (COLUMNAS_REGISTRO): organismo, recurso (ID en la
    fuente, si tiene), archivo (nombre lógico del crudo), version (ruta de la copia guardada), url,
    fecha_publicacion, origen_fecha (de dónde sale la fecha), etag, fecha_descarga, bytes y sha256
    (del archivo original).

Fuentes: cualquiera. Lo usan los lectores (lectores/) y, hasta que se migren, scripts/.
Genera: datos/crudos/<organismo>/versiones/ (no va a Git) y datos/registros/versiones_crudos.csv (va a Git).
"""

from __future__ import annotations

import gzip
import hashlib
import io
import re
import shutil
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

# Carpetas del repositorio (este archivo está en <raiz>/comun/)
RAIZ = Path(__file__).resolve().parents[1]
CRUDOS = RAIZ / "datos" / "crudos"
PROCESADOS = RAIZ / "datos" / "procesados"  # hasta la migración de los Pasos 3b y 3c
REGISTRO_VERSIONES = RAIZ / "datos" / "registros" / "versiones_crudos.csv"

COLUMNAS_REGISTRO = ["organismo", "recurso", "archivo", "version", "url", "fecha_publicacion", "origen_fecha",
                     "etag", "fecha_descarga", "bytes", "sha256"]

# Encabezado genérico: algunos sitios rechazan pedidos sin "User-Agent".
ENCABEZADOS = {"User-Agent": "Mozilla/5.0 (compatible; descarga-datos-publicos/1.0)"}
ZONA_HORARIA = ZoneInfo("America/Argentina/Buenos_Aires")
LIMITE_SIN_OK_BYTES = 1_000_000_000  # regla 8 del instructivo: más de 1 GB en total requiere el ok de Agustín
# Regla 8 (precisada el 25/11/2026): una fuente sin fecha de publicación ni ETag se baja solo si es
# chica (menos de 50 MB según lo que informa la fuente o, si no lo informa, según la última versión).
LIMITE_SIN_FECHA_BYTES = 50_000_000
ORIGEN_SIN_FECHA = "sin fecha ni ETag de la fuente: se usa la fecha de descarga"
ORIGEN_SIN_FECHA_SIN_CAMBIOS = "sin fecha ni ETag de la fuente: verificada por hash en la fecha de descarga, sin cambios"

# Modo de la corrida (lo fija actualizar.py con configurar()).
_MODO = {"sin_descargar": False, "crudos_al": None, "ok_mas_de_1gb": False}


class DescargaFrenada(RuntimeError):
    """Se frena antes de bajar: la fuente no informa fecha de publicación ni ETag (no se puede saber
    si cambió), no respondió, o lo que hay que bajar supera 1 GB sin ok (regla 8 del instructivo)."""


def configurar(sin_descargar: bool = False, crudos_al: str | None = None, ok_mas_de_1gb: bool = False) -> None:
    """Modo de la corrida: sin_descargar usa las últimas versiones bajadas, sin internet;
    crudos_al ("AAAA-MM-DD") usa, de cada crudo, la última versión bajada hasta esa fecha (lo que
    teníamos ese día);
    ok_mas_de_1gb es el ok de Agustín para bajar más de 1 GB en esta corrida (regla 8)."""
    _MODO["sin_descargar"] = bool(sin_descargar)
    _MODO["crudos_al"] = crudos_al
    _MODO["ok_mas_de_1gb"] = bool(ok_mas_de_1gb)


# ---------------------------------------------------------------------------------------------
# Descarga y hash
# ---------------------------------------------------------------------------------------------
def sha256_de(ruta: Path) -> str:
    """SHA-256 del contenido original: si la ruta es una versión .gz, del contenido descomprimido."""
    hash_ = hashlib.sha256()
    abrir = gzip.open if Path(ruta).suffix == ".gz" else open
    with abrir(ruta, "rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            hash_.update(bloque)
    return hash_.hexdigest()


def descargar(url: str, destino: Path, reusar_si_existe: bool = False,
              intentos: int = 3, timeout: int = 120) -> dict:
    """Baja `url` a `destino` y devuelve un registro de la descarga.

    - Escribe por partes (streaming), así funciona también con archivos grandes.
    - Si `reusar_si_existe` es True y el archivo ya está, no lo vuelve a bajar
      (lo usa la descarga condicional para calcular el hash del archivo local).
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
    return {
        "archivo": Path(destino).relative_to(RAIZ).as_posix(),
        "url": url,
        "fecha_descarga": fecha.strftime("%Y-%m-%d %H:%M"),
        "bytes": Path(destino).stat().st_size,
        "sha256": sha256_de(destino),
        "reusado_de_corrida_anterior": reusado,
    }


def guardar_registro(registros: list[dict], ruta_csv: Path) -> None:
    """Guarda la lista de descargas de una corrida en un CSV."""
    ruta_csv = Path(ruta_csv)
    ruta_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(registros).to_csv(ruta_csv, index=False)


# ---------------------------------------------------------------------------------------------
# Versiones
# ---------------------------------------------------------------------------------------------
def leer_registro() -> pd.DataFrame:
    """El registro de versiones, con todas las columnas (vacío si todavía no existe)."""
    if not REGISTRO_VERSIONES.exists():
        return pd.DataFrame(columns=COLUMNAS_REGISTRO)
    registro = pd.read_csv(REGISTRO_VERSIONES, dtype={c: "string" for c in COLUMNAS_REGISTRO if c != "bytes"})
    return registro.reindex(columns=COLUMNAS_REGISTRO)


def _anotar(fila: dict) -> None:
    REGISTRO_VERSIONES.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([fila]).reindex(columns=COLUMNAS_REGISTRO).to_csv(
        REGISTRO_VERSIONES, mode="a", header=not REGISTRO_VERSIONES.exists(), index=False)


def _organismo(archivo: str) -> str | None:
    partes = Path(archivo).parts  # datos/crudos/<organismo>/...
    return partes[2] if len(partes) > 3 and partes[:2] == ("datos", "crudos") else None


def _recurso_ckan(url: str) -> str | None:
    encontrado = re.search(r"/resource/([0-9a-f-]{36})/", url or "")
    return encontrado.group(1) if encontrado else None


def comprimir(origen: Path, destino: Path) -> None:
    """Copia `origen` comprimido con gzip en `destino` (primero a un temporal, después lo renombra)."""
    temporal = destino.with_name(destino.name + ".parcial")
    with open(origen, "rb") as entrada, gzip.open(temporal, "wb", compresslevel=6) as salida:
        shutil.copyfileobj(entrada, salida, 1024 * 1024)
    temporal.replace(destino)


def guardar_version(registro: dict, fecha_publicacion: str | None, origen_fecha: str | None = None,
                    etag: str | None = None, organismo: str | None = None, recurso: str | None = None,
                    origen: Path | None = None) -> dict:
    """Guarda una copia comprimida del archivo descargado como versión, sin pisar ninguna anterior.

    - La copia va a <carpeta del archivo>/versiones/<nombre>__<fecha>__<hash 12>.<ext>.gz. La fecha es la
      de publicación que informa la fuente; si no la informa, la de descarga (y origen_fecha lo dice).
    - Si ya hay una versión con ese hash (comprimida, o sin comprimir de antes del Paso 3a), no se
      copia de nuevo. Si la fuente la republicó con otra fecha u otro ETag, se anota igual en el
      registro (apunta a la versión ya guardada): así la descarga condicional no la vuelve a bajar.
    - `origen` es el archivo descargado, si no está en la ruta lógica `registro["archivo"]`.
    Devuelve el registro con la ruta de la versión y si es nueva.
    """
    logico = RAIZ / registro["archivo"]
    origen = Path(origen) if origen else logico
    carpeta = logico.parent / "versiones"
    carpeta.mkdir(parents=True, exist_ok=True)
    fecha = (fecha_publicacion or registro["fecha_descarga"])[:10]
    corto = registro["sha256"][:12]
    ya_guardadas = sorted(carpeta.glob(f"{logico.stem}__*__{corto}{logico.suffix}*"))
    ya_guardadas = [v for v in ya_guardadas if not v.name.endswith(".parcial")]
    nueva = not ya_guardadas
    version = ya_guardadas[0] if ya_guardadas else carpeta / f"{logico.stem}__{fecha}__{corto}{logico.suffix}.gz"
    if nueva:
        comprimir(origen, version)
        if sha256_de(version) != registro["sha256"]:
            raise RuntimeError(f"La versión comprimida {version} no reproduce el hash del original")

    if origen_fecha is None:
        if fecha_publicacion and _recurso_ckan(registro["url"]):
            origen_fecha = "portal CKAN (last_modified)"
        elif fecha_publicacion:
            origen_fecha = "informada por la fuente"
        else:
            origen_fecha = "sin fecha de la fuente: se usa la de descarga"
    anotadas = leer_registro()
    misma = ((anotadas["archivo"] == registro["archivo"]) & (anotadas["sha256"] == registro["sha256"])
             & (anotadas["fecha_publicacion"].fillna("") == (fecha_publicacion or ""))
             & (anotadas["etag"].fillna("") == (etag or "")))
    if nueva or ((fecha_publicacion or etag) and not misma.any()):
        _anotar({"organismo": organismo or _organismo(registro["archivo"]),
                 "recurso": recurso or _recurso_ckan(registro["url"]),
                 "archivo": registro["archivo"], "version": version.relative_to(RAIZ).as_posix(),
                 "url": registro["url"], "fecha_publicacion": fecha_publicacion, "origen_fecha": origen_fecha,
                 "etag": etag, "fecha_descarga": registro["fecha_descarga"], "bytes": registro["bytes"],
                 "sha256": registro["sha256"]})
    return {**registro, "version": version.relative_to(RAIZ).as_posix(), "version_nueva": nueva,
            "fecha_publicacion": fecha_publicacion}


def version_registrada(archivo: Path | str, al: str | None = None) -> dict:
    """La última versión BAJADA de un crudo (por fecha de descarga), o la última bajada hasta `al`
    ("AAAA-MM-DD", inclusive): reconstruye lo que teníamos en esa fecha (criterio aprobado por
    Agustín el 25/11/2026). Frena si no hay ninguna o si falta la copia."""
    archivo = Path(archivo)
    logico = (archivo.relative_to(RAIZ) if archivo.is_absolute() else archivo).as_posix()
    filas = leer_registro()
    filas = filas[filas["archivo"] == logico]
    if al:
        filas = filas[filas["fecha_descarga"].str[:10] <= al]
    if filas.empty:
        raise DescargaFrenada(f"No hay ninguna versión registrada de {logico}" + (f" bajada hasta el {al}" if al else ""))
    ultima = filas.sort_values("fecha_descarga", kind="stable").iloc[-1]
    if not (RAIZ / ultima["version"]).exists():
        raise DescargaFrenada(f"Falta la copia {ultima['version']} registrada para {logico}")
    return {**ultima.to_dict(), "descargado": False}


def leer_bytes(version: Path | str) -> io.BytesIO:
    """El contenido original de una versión (la descomprime si es .gz). Sirve para read_excel."""
    ruta = RAIZ / version if not Path(version).is_absolute() else Path(version)
    abrir = gzip.open if ruta.suffix == ".gz" else open
    with abrir(ruta, "rb") as archivo:
        return io.BytesIO(archivo.read())


# ---------------------------------------------------------------------------------------------
# Descarga condicional para fuentes HTTP (INDEC, BCRA, ...)
# ---------------------------------------------------------------------------------------------
def metadatos_http(url: str) -> dict | None:
    """Solo los encabezados (HEAD): Last-Modified (como fecha ISO), ETag y tamaño. None si no responde."""
    try:
        respuesta = requests.head(url, headers=ENCABEZADOS, timeout=60, allow_redirects=True)
        respuesta.raise_for_status()
    except requests.RequestException:
        return None
    ultima_modificacion = respuesta.headers.get("Last-Modified")
    if ultima_modificacion:
        try:
            ultima_modificacion = parsedate_to_datetime(ultima_modificacion).isoformat()
        except (TypeError, ValueError):
            ultima_modificacion = None
    tamanio = respuesta.headers.get("Content-Length")
    return {"fecha_publicacion": ultima_modificacion, "etag": respuesta.headers.get("ETag"),
            "bytes": int(tamanio) if tamanio and tamanio.isdigit() else None}


def _ultima_fila(logico: str) -> pd.Series | None:
    filas = leer_registro()
    filas = filas[filas["archivo"] == logico]
    if filas.empty:
        return None
    orden = filas["fecha_publicacion"].fillna(filas["fecha_descarga"]).str[:10]
    return filas.assign(_orden=orden).sort_values(["_orden", "fecha_descarga"], kind="stable").iloc[-1]


def _misma_publicacion(fila: pd.Series, metadatos: dict) -> bool:
    if metadatos["fecha_publicacion"]:
        return fila["fecha_publicacion"] == metadatos["fecha_publicacion"]
    return bool(metadatos["etag"]) and fila["etag"] == metadatos["etag"]


def descargar_condicional(url: str, organismo: str, nombre: str, recurso: str | None = None) -> dict:
    """Baja `url` solo si cambió, y la guarda como versión comprimida (sin copia "vigente").

    - Si la corrida es sin descargar o con crudos al AAAA-MM-DD, no usa internet: devuelve la versión
      registrada que corresponde.
    - Pide los encabezados: si el Last-Modified (o, si no hay, el ETag) es el de la última versión
      registrada y la copia existe, no baja nada.
    - Si la fuente no responde, frena. Si no informa Last-Modified ni ETag, aplica la regla 8 (a) y
      (b): ver _descargar_sin_fecha().
    Devuelve el registro de la versión (con "version", la ruta de la copia, y "descargado")."""
    logico = CRUDOS / organismo / nombre
    relativo = logico.relative_to(RAIZ).as_posix()
    if _MODO["sin_descargar"] or _MODO["crudos_al"]:
        return version_registrada(relativo, _MODO["crudos_al"])
    metadatos = metadatos_http(url)
    if metadatos is None:
        raise DescargaFrenada(f"La fuente no respondió los encabezados de {url}: {nombre} queda sin verificar.")
    ultima = _ultima_fila(relativo)
    if not metadatos["fecha_publicacion"] and not metadatos["etag"]:
        return _descargar_sin_fecha(url, logico, relativo, organismo, recurso, metadatos, ultima)
    if ultima is not None and _misma_publicacion(ultima, metadatos) and (RAIZ / ultima["version"]).exists():
        return {**ultima.drop(labels="_orden").to_dict(), "descargado": False}
    temporal = logico.with_name(logico.name + ".descarga")
    registro = descargar(url, temporal)
    registro["archivo"] = relativo
    origen_fecha = "encabezado Last-Modified" if metadatos["fecha_publicacion"] else "sin Last-Modified: se usa la de descarga (cambio detectado por ETag)"
    resultado = guardar_version(registro, metadatos["fecha_publicacion"], origen_fecha=origen_fecha,
                                etag=metadatos["etag"], organismo=organismo, recurso=recurso, origen=temporal)
    temporal.unlink()  # el archivo descargado ya quedó como versión comprimida (no se guarda copia "vigente")
    return {**resultado, "descargado": True}


def tamanio_conocido(metadatos: dict, ultima: pd.Series | None) -> int | None:
    """Lo que pesa el recurso: lo que informa la fuente (Content-Length) o, si no lo informa, la
    última versión registrada. None si no se puede saber."""
    if metadatos.get("bytes") is not None:
        return int(metadatos["bytes"])
    if ultima is not None and pd.notna(ultima["bytes"]):
        return int(ultima["bytes"])
    return None


def _descargar_sin_fecha(url: str, logico: Path, relativo: str, organismo: str, recurso: str | None,
                         metadatos: dict, ultima: pd.Series | None) -> dict:
    """Regla 8 (a) y (b): la fuente no informa fecha de publicación ni ETag.
    - Si se sabe que pesa menos de 50 MB: se baja y se compara el hash con las versiones guardadas.
      Si es una versión que ya estaba, solo se anota la verificación (una fila en el registro que
      apunta a esa versión); si cambió, se guarda la versión nueva con la fecha de descarga.
    - Si es grande o no se puede saber cuánto pesa: frena sin bajar."""
    tamanio = tamanio_conocido(metadatos, ultima)
    if tamanio is None or tamanio >= LIMITE_SIN_FECHA_BYTES:
        cuanto = "no se puede saber cuánto pesa" if tamanio is None else f"pesa {tamanio / 1e6:.1f} MB (50 MB o más)"
        raise DescargaFrenada(f"{url} no informa fecha de publicación ni ETag y {cuanto}: no se baja a ciegas "
                              f"(regla 8 del instructivo).")
    temporal = logico.with_name(logico.name + ".descarga")
    registro = descargar(url, temporal)
    registro["archivo"] = relativo
    resultado = guardar_version(registro, None, origen_fecha=ORIGEN_SIN_FECHA, organismo=organismo,
                                recurso=recurso, origen=temporal)
    temporal.unlink()  # el contenido quedó como versión comprimida (nueva o ya guardada)
    if not resultado["version_nueva"]:
        _anotar({"organismo": organismo, "recurso": recurso, "archivo": relativo, "version": resultado["version"],
                 "url": url, "fecha_publicacion": None, "origen_fecha": ORIGEN_SIN_FECHA_SIN_CAMBIOS, "etag": None,
                 "fecha_descarga": registro["fecha_descarga"], "bytes": registro["bytes"], "sha256": registro["sha256"]})
    return {**resultado, "descargado": True}


def revisar_http(archivos: list[tuple[str, str, str]]) -> pd.DataFrame:
    """Sin bajar nada: para cada (organismo, nombre, url), compara los encabezados con la última
    versión registrada. estado: "sin cambios", "cambió", "nuevo" o "sin respuesta"; si la fuente no
    informa Last-Modified ni ETag, "sin fecha, chica" (menos de 50 MB: se baja y se compara el hash)
    o "sin fecha, grande o sin tamaño" (frena). bytes_a_bajar: el Content-Length, o el de la última versión."""
    filas = []
    for organismo, nombre, url in archivos:
        relativo = (CRUDOS / organismo / nombre).relative_to(RAIZ).as_posix()
        ultima = _ultima_fila(relativo)
        metadatos = metadatos_http(url)
        bytes_registrados = None if ultima is None else int(ultima["bytes"])
        if metadatos is None:
            estado, tamanio = "sin respuesta", bytes_registrados
        elif not metadatos["fecha_publicacion"] and not metadatos["etag"]:
            tamanio = tamanio_conocido(metadatos, ultima)
            chica = tamanio is not None and tamanio < LIMITE_SIN_FECHA_BYTES
            estado = "sin fecha, chica" if chica else "sin fecha, grande o sin tamaño"
        else:
            tamanio = metadatos["bytes"] or bytes_registrados
            estado = "nuevo" if ultima is None else ("sin cambios" if _misma_publicacion(ultima, metadatos) else "cambió")
        filas.append({"archivo": relativo, "url": url, "estado": estado,
                      "publicacion_registrada": None if ultima is None else ultima["fecha_publicacion"],
                      "publicacion_fuente": None if metadatos is None else metadatos["fecha_publicacion"],
                      "bytes_registrados": bytes_registrados, "bytes_a_bajar": tamanio})
    return pd.DataFrame(filas)


def autorizar_descarga(revision: pd.DataFrame, ok_mas_de_1gb: bool | None = None) -> pd.DataFrame:
    """Frena (DescargaFrenada) si algún archivo no se puede verificar (sin respuesta o sin fecha), o si
    lo que cambió supera 1 GB y no hay ok (si no se pasa, vale el de la corrida: configurar()).
    Devuelve los archivos que hay que bajar."""
    if ok_mas_de_1gb is None:
        ok_mas_de_1gb = _MODO["ok_mas_de_1gb"]
    sin_verificar = revision[revision["estado"].isin(["sin respuesta", "sin fecha, grande o sin tamaño"])]
    if len(sin_verificar):
        total = sin_verificar["bytes_a_bajar"].fillna(0).sum()
        raise DescargaFrenada(
            "Estos archivos no se pueden verificar (la fuente no respondió, o no informa Last-Modified ni ETag y es "
            f"grande o no se sabe cuánto pesa) y no se bajan sin el ok de Agustín ({total / 1e9:.2f} GB en total):\n"
            + sin_verificar[["archivo", "estado", "publicacion_registrada", "bytes_a_bajar"]].to_string(index=False))
    a_bajar = revision[revision["estado"].isin(["cambió", "nuevo", "sin fecha, chica"])]
    total = a_bajar["bytes_a_bajar"].fillna(0).sum()
    if total > LIMITE_SIN_OK_BYTES and not ok_mas_de_1gb:
        raise DescargaFrenada(
            f"Hay que bajar {total / 1e9:.2f} GB (más de 1 GB): falta el ok de Agustín (regla 8 del instructivo).\n"
            + a_bajar[["archivo", "publicacion_registrada", "publicacion_fuente", "bytes_a_bajar"]].to_string(index=False))
    return a_bajar
