"""
Catálogo de series (código común, sin criterios económicos).

Qué hace:
    - armadores(): encuentra los armadores de bloques/<bloque>/*.py. Un armador es un módulo que declara:
        SERIES       lista de series que produce (una por columna de un CSV de datos/series/<bloque>/),
                     cada una con los campos de CAMPOS_DECLARADOS;
        AUXILIARES   (opcional) {archivo: [columnas que no son series]}, por ejemplo dias_del_mes;
        DEPENDE_DE   (opcional) ids de series de otros armadores que usa;
        FORMATO      (opcional) {archivo: formato de los números al escribir, por ejemplo "%.4f"};
        armar()      devuelve {"series": {archivo: tabla con índice fecha}, "controles": tabla
                     (control, estado, detalle, alcance), "validacion": {nombre: tabla o texto},
                     "registros": [registros de descarga, con fecha_publicacion y sha256]}.
    - validar_declaracion(): que cada serie declare todos los campos y con valores válidos.
    - resolver(): qué armadores corren y en qué orden (todo, un bloque o una serie, más lo que necesitan).
    - armar_catalogo(): arma catalogo_series.csv: los campos que declara cada armador, el inicio y el
      fin leídos de los archivos de datos/series/, los datos de la última corrida de cada armador
      (publicación y hash de los crudos, controles a revisar) y el estado de auditoría, que sale de
      datos/registros/auditorias.csv (lo único que se carga a mano).
    - verificar_catalogo(): toda columna de serie de datos/series/ tiene su fila en el catálogo y
      toda fila del catálogo apunta a una columna que existe (test de los dos sentidos).

Columnas del catálogo (COLUMNAS_CATALOGO): las de la propuesta de arquitectura (sección 3) más uso
    (base o control), discontinuada y con_reservas (criterios, sección 10), y rotulo (oficial, no
    oficial, no oficial (académica), regulado o estimación propia; regla 4 del instructivo). inicio
    es el primer dato no vacío de la serie, leído del archivo.
Columnas de datos/registros/auditorias.csv (COLUMNAS_AUDITORIAS): fecha, alcance ("todo", un bloque, un
    archivo del bloque como "energia.produccion_vaca_muerta_mensual", o el id de una serie), commit,
    resultado (aprobada, con observaciones o rechazada) y notas.

Fuentes: ninguna (lee lo que declaran los armadores y los archivos de datos/series/).
Genera: catalogo_series.csv (lo escribe actualizar.py).
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from types import ModuleType

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]

CAMPOS_DECLARADOS = ["archivo", "columna", "nombre", "unidad", "frecuencia", "tipo", "precios", "ajuste_estacional",
                     "uso", "organismo", "rotulo", "fuente_id", "fuente_url", "lector", "criterio", "estimados",
                     "tiene_revisiones", "discontinuada", "con_reservas", "informe_validacion"]
VALORES_VALIDOS = {
    "frecuencia": {"diaria", "mensual", "trimestral", "semestral", "anual"},
    "tipo": {"nivel", "saldo", "índice", "variación", "tasa"},
    "precios": {"corrientes", "constantes", "no aplica"},
    "ajuste_estacional": {"original", "desestacionalizada", "tendencia-ciclo"},
    "uso": {"base", "control"},
    # Rótulo de la fuente (regla 4 del instructivo; aprobado por Agustín el 25/11/2026).
    "rotulo": {"oficial", "no oficial", "no oficial (académica)", "regulado", "estimación propia"},
    "discontinuada": {"sí", "no"},
    "con_reservas": {"sí", "no"},
}
COLUMNAS_CATALOGO = ["id", "nombre", "bloque", "archivo", "columna", "unidad", "frecuencia", "tipo", "precios",
                     "ajuste_estacional", "uso", "organismo", "rotulo", "fuente_id", "fuente_url", "lector", "armador", "criterio",
                     "estimados", "tiene_revisiones", "inicio", "fin", "discontinuada", "con_reservas",
                     "publicacion_fuente", "version_crudo", "ultima_actualizacion", "controles_a_revisar",
                     "estado_validacion", "informe_validacion"]
CAMPOS_DE_CORRIDA = ["publicacion_fuente", "version_crudo", "ultima_actualizacion", "controles_a_revisar"]
COLUMNAS_AUDITORIAS = ["fecha", "alcance", "commit", "resultado", "notas"]


@dataclass
class Armador:
    bloque: str
    nombre: str
    ruta: str                      # relativa a la raíz, por ejemplo bloques/energia/produccion.py
    modulo: ModuleType
    series: list[dict]
    auxiliares: dict = field(default_factory=dict)
    depende_de: list = field(default_factory=list)
    formato: dict = field(default_factory=dict)


def id_serie(bloque: str, archivo: str, columna: str) -> str:
    return f"{bloque}.{Path(archivo).stem}.{columna}"


def desde_modulo(modulo: ModuleType, bloque: str, nombre: str, ruta: str) -> Armador:
    """Arma la descripción de un armador a partir de lo que declara su módulo (y la valida)."""
    series = [{**s, "id": id_serie(bloque, s["archivo"], s["columna"])} for s in getattr(modulo, "SERIES")]
    armador = Armador(bloque=bloque, nombre=nombre, ruta=ruta, modulo=modulo, series=series,
                      auxiliares=dict(getattr(modulo, "AUXILIARES", {})), depende_de=list(getattr(modulo, "DEPENDE_DE", [])),
                      formato=dict(getattr(modulo, "FORMATO", {})))
    validar_declaracion(armador)
    return armador


def armadores(raiz: Path = RAIZ) -> list[Armador]:
    """Todos los armadores de bloques/<bloque>/*.py (módulos con SERIES y armar())."""
    encontrados = []
    for ruta in sorted((Path(raiz) / "bloques").glob("*/*.py")):
        if ruta.name.startswith("_"):
            continue
        modulo = importlib.import_module(f"bloques.{ruta.parent.name}.{ruta.stem}")
        if hasattr(modulo, "SERIES") and hasattr(modulo, "armar"):
            encontrados.append(desde_modulo(modulo, ruta.parent.name, ruta.stem, ruta.relative_to(raiz).as_posix()))
    return encontrados


def validar_declaracion(armador: Armador) -> None:
    """Cada serie declara todos los campos, con valores válidos, y sin ids repetidos."""
    problemas = []
    for serie in armador.series:
        faltan = [c for c in CAMPOS_DECLARADOS if c not in serie or serie[c] in (None, "")]
        if faltan:
            problemas.append(f"{serie.get('id')}: faltan {faltan}")
        for campo, validos in VALORES_VALIDOS.items():
            if campo in serie and serie[campo] not in validos:
                problemas.append(f"{serie.get('id')}: {campo} = {serie[campo]!r} no es uno de {sorted(validos)}")
    ids = [s["id"] for s in armador.series]
    repetidos = sorted({i for i in ids if ids.count(i) > 1})
    if repetidos:
        problemas.append(f"ids repetidos: {repetidos}")
    if problemas:
        raise ValueError(f"Declaración inválida en {armador.ruta}:\n  " + "\n  ".join(problemas))


def resolver(lista: list[Armador], bloque: str | None = None, serie: str | None = None) -> list[Armador]:
    """Armadores a correr, en orden: los pedidos (todos, un bloque o el de una serie) más los que
    producen las series de las que dependen. Frena si falta una dependencia o hay un ciclo."""
    productor = {s["id"]: a for a in lista for s in a.series}
    if serie:
        if serie not in productor:
            raise ValueError(f"Ninguna serie con id {serie}")
        pedidos = [productor[serie]]
    elif bloque:
        pedidos = [a for a in lista if a.bloque == bloque]
        if not pedidos:
            raise ValueError(f"El bloque {bloque} no tiene armadores")
    else:
        pedidos = list(lista)
    elegidos, pendientes = {}, list(pedidos)
    while pendientes:
        armador = pendientes.pop()
        if armador.ruta in elegidos:
            continue
        elegidos[armador.ruta] = armador
        for dependencia in armador.depende_de:
            if dependencia not in productor:
                raise ValueError(f"{armador.ruta} depende de {dependencia}, que ningún armador produce")
            pendientes.append(productor[dependencia])
    orden, hechos = [], set()
    while len(orden) < len(elegidos):
        listos = [a for r, a in sorted(elegidos.items()) if r not in hechos
                  and all(productor[d].ruta in hechos for d in a.depende_de)]
        if not listos:
            raise ValueError("Hay un ciclo de dependencias entre: " + ", ".join(sorted(set(elegidos) - hechos)))
        for armador in listos:
            orden.append(armador)
            hechos.add(armador.ruta)
    return orden


def ruta_serie(bloque: str, archivo: str, raiz: Path = RAIZ) -> Path:
    return Path(raiz) / "datos" / "series" / bloque / archivo


# Raíz de la corrida (la fija actualizar.py): de ahí leen los armadores las series de otros bloques.
_RAIZ_DE_LA_CORRIDA = {"raiz": RAIZ}


def usar_raiz(raiz: Path) -> None:
    _RAIZ_DE_LA_CORRIDA["raiz"] = Path(raiz)


def leer_serie(bloque: str, archivo: str, indice_fecha: bool = True) -> pd.DataFrame:
    """Lee un CSV de datos/series/<bloque>/ (de la raíz de la corrida), con la primera columna como
    índice (convertida a fecha si `indice_fecha`). Es como un armador usa las series de otro bloque."""
    tabla = pd.read_csv(ruta_serie(bloque, archivo, _RAIZ_DE_LA_CORRIDA["raiz"]), index_col=0)
    if indice_fecha:
        tabla.index = pd.to_datetime(tabla.index)
    return tabla


def leer_catalogo(raiz: Path = RAIZ) -> pd.DataFrame:
    ruta = Path(raiz) / "catalogo_series.csv"
    if not ruta.exists():
        return pd.DataFrame(columns=COLUMNAS_CATALOGO)
    return pd.read_csv(ruta, dtype=str).reindex(columns=COLUMNAS_CATALOGO)


def escribir_catalogo(catalogo: pd.DataFrame, raiz: Path = RAIZ) -> None:
    catalogo.reindex(columns=COLUMNAS_CATALOGO).to_csv(Path(raiz) / "catalogo_series.csv", index=False)


def leer_auditorias(raiz: Path = RAIZ) -> pd.DataFrame:
    ruta = Path(raiz) / "datos" / "registros" / "auditorias.csv"
    if not ruta.exists():
        return pd.DataFrame(columns=COLUMNAS_AUDITORIAS)
    return pd.read_csv(ruta, dtype=str).reindex(columns=COLUMNAS_AUDITORIAS)


def _inicio_fin(ruta: Path, columna: str) -> tuple[str, str]:
    if not ruta.exists():
        return "", ""
    tabla = pd.read_csv(ruta, dtype=str)
    if columna not in tabla.columns:
        return "", ""
    fechas = tabla.loc[tabla[columna].notna() & (tabla[columna] != ""), tabla.columns[0]]
    return (fechas.iloc[0], fechas.iloc[-1]) if len(fechas) else ("", "")


def alcance_aplica(alcance: str, serie_id: str) -> bool:
    """El alcance de una auditoría cubre la serie si es "todo", su bloque ("energia"), su archivo
    ("energia.produccion_vaca_muerta_mensual") o la serie misma (id completo)."""
    return alcance == "todo" or serie_id == alcance or serie_id.startswith(f"{alcance}.")


def _estado_validacion(serie_id: str, bloque: str, controles_a_revisar: str, auditorias: pd.DataFrame) -> str:
    aplica = auditorias["alcance"].fillna("").map(lambda a: alcance_aplica(a, serie_id))
    aplican = auditorias[aplica & (auditorias["resultado"] == "aprobada")]
    if len(aplican):
        ultima = aplican.iloc[-1]
        return f"auditada {ultima['fecha']}, {ultima['commit']}"
    return "controles OK" if str(controles_a_revisar) == "0" else "sin validar"


def armar_catalogo(lista: list[Armador], corridas: dict, anterior: pd.DataFrame, auditorias: pd.DataFrame,
                   raiz: Path = RAIZ) -> pd.DataFrame:
    """Una fila por serie declarada. `corridas`: {ruta del armador: datos de esta corrida} solo para los
    armadores que escribieron sus series en esta corrida; para los demás se conservan los datos de
    corrida del catálogo anterior."""
    anterior = anterior.set_index("id") if len(anterior) else anterior
    filas = []
    for armador in lista:
        corrida = corridas.get(armador.ruta)
        for serie in armador.series:
            fila = {c: serie[c] for c in CAMPOS_DECLARADOS if c not in ("archivo",)}
            fila.update({"id": serie["id"], "bloque": armador.bloque, "armador": armador.ruta,
                         "archivo": ruta_serie(armador.bloque, serie["archivo"], raiz).relative_to(raiz).as_posix()})
            fila["inicio"], fila["fin"] = _inicio_fin(ruta_serie(armador.bloque, serie["archivo"], raiz), serie["columna"])
            if corrida:
                fila.update({c: corrida.get(c, "") for c in CAMPOS_DE_CORRIDA})
            elif len(anterior) and serie["id"] in anterior.index:
                fila.update({c: anterior.loc[serie["id"], c] for c in CAMPOS_DE_CORRIDA})
            else:
                fila.update({c: "" for c in CAMPOS_DE_CORRIDA})
            fila["estado_validacion"] = _estado_validacion(serie["id"], armador.bloque, fila["controles_a_revisar"], auditorias)
            filas.append(fila)
    return pd.DataFrame(filas, columns=COLUMNAS_CATALOGO)


def datos_de_corrida(registros: list[dict], controles: pd.DataFrame) -> dict:
    """Campos de corrida del catálogo para un armador que escribió sus series."""
    publicadas = sorted({str(r.get("fecha_publicacion"))[:10] for r in registros if r.get("fecha_publicacion")})
    hashes = sorted({str(r.get("sha256"))[:12] for r in registros if r.get("sha256")})
    return {"publicacion_fuente": "; ".join(publicadas), "version_crudo": "; ".join(hashes),
            "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d"),
            "controles_a_revisar": str(int(controles["estado"].isin(["REVISAR", "DIFERENCIAS"]).sum()))}


def verificar_catalogo(catalogo: pd.DataFrame, lista: list[Armador], raiz: Path = RAIZ) -> tuple[list, list]:
    """Toda columna de serie de datos/series/<bloque>/*.csv tiene su fila en el catálogo, y toda fila
    del catálogo apunta a una columna que existe. Devuelve (faltan en el catálogo, sobran en el catálogo).
    No son series la primera columna (la fecha) ni las AUXILIARES que declara el armador del archivo."""
    auxiliares = {ruta_serie(a.bloque, archivo, raiz).relative_to(raiz).as_posix(): set(columnas)
                  for a in lista for archivo, columnas in a.auxiliares.items()}
    en_disco = set()
    for ruta in sorted((Path(raiz) / "datos" / "series").glob("*/*.csv")):
        relativa = ruta.relative_to(raiz).as_posix()
        columnas = list(pd.read_csv(ruta, nrows=0).columns)[1:]
        en_disco |= {(relativa, c) for c in columnas if c not in auxiliares.get(relativa, set())}
    en_catalogo = set(zip(catalogo["archivo"], catalogo["columna"]))
    return sorted(en_disco - en_catalogo), sorted(en_catalogo - en_disco)
