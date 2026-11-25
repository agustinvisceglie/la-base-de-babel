"""
Controles comunes (código común, sin criterios económicos).

Qué hace:
    - Estados de un control (los mismos que en producción):
        OK          el control dio bien;
        REVISAR     falla estructural (unidades, meses faltantes, corte, lectura distinta de lo
                    publicado): BLOQUEA, salvo que haya una excepción aprobada;
        DIFERENCIAS diferencias conocidas y documentadas (por ejemplo, con otra fuente): no bloquea;
        EVIDENCIA   contraste informativo (primera publicación vs. vigente, hipótesis): no bloquea.
    - leer_excepciones() y bloqueantes(): un control en REVISAR frena la escritura de las series del
      armador, salvo que datos/registros/excepciones.csv tenga una excepción con estado "aprobada"
      para el mismo bloque, el mismo control y el mismo alcance (regla 6 del instructivo). Las
      excepciones las propone Code (estado "propuesta") y las aprueba Agustín; este código nunca
      cambia el estado de una excepción.
    - verificar_corte(): ninguna serie puede tener meses posteriores al último mes completo de la fuente.
    - registrar_corrida(): agrega una fila a datos/registros/corridas.csv por cada corrida de actualizar.py.

Columnas de datos/registros/excepciones.csv (COLUMNAS_EXCEPCIONES):
    id, bloque, control (texto exacto del control), alcance (qué meses o casos cubre, texto exacto
    del alcance que informa el control; vacío si el control no informa alcance), motivo, evidencia
    (archivo o informe que la respalda), estado (propuesta, aprobada o rechazada), fecha_propuesta,
    fecha_auditoria y auditoria (quién y dónde la aprobó o rechazó).
Columnas de datos/registros/corridas.csv (COLUMNAS_CORRIDAS): ver abajo.

Fuentes: ninguna.
Genera: filas en datos/registros/corridas.csv.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
REGISTROS = RAIZ / "datos" / "registros"

ESTADOS = {"OK": False, "REVISAR": True, "DIFERENCIAS": False, "EVIDENCIA": False}  # True = bloquea
COLUMNAS_CONTROLES = ["control", "estado", "detalle", "alcance"]
COLUMNAS_EXCEPCIONES = ["id", "bloque", "control", "alcance", "motivo", "evidencia", "estado",
                        "fecha_propuesta", "fecha_auditoria", "auditoria"]
ESTADOS_EXCEPCION = ["propuesta", "aprobada", "rechazada"]
COLUMNAS_CORRIDAS = ["inicio", "fin", "duracion_segundos", "comando", "modo", "armadores", "armadores_escritos",
                     "armadores_frenados", "controles_bloqueantes", "controles_cubiertos_por_excepcion",
                     "controles_a_revisar", "versiones_nuevas_de_crudos", "resultado"]


def normalizar_controles(tabla: pd.DataFrame) -> pd.DataFrame:
    """Controles con las columnas comunes (alcance vacío si el armador no lo informa) y estados válidos."""
    tabla = tabla.reindex(columns=COLUMNAS_CONTROLES + [c for c in tabla.columns if c not in COLUMNAS_CONTROLES])
    tabla["alcance"] = tabla["alcance"].fillna("").astype(str)
    desconocidos = set(tabla["estado"]) - set(ESTADOS)
    if desconocidos:
        raise ValueError(f"Estados de control desconocidos: {sorted(desconocidos)} (válidos: {list(ESTADOS)})")
    return tabla


def leer_excepciones(raiz: Path = RAIZ) -> pd.DataFrame:
    ruta = Path(raiz) / "datos" / "registros" / "excepciones.csv"
    if not ruta.exists():
        return pd.DataFrame(columns=COLUMNAS_EXCEPCIONES)
    excepciones = pd.read_csv(ruta, dtype=str).reindex(columns=COLUMNAS_EXCEPCIONES)
    excepciones["alcance"] = excepciones["alcance"].fillna("")
    invalidos = set(excepciones["estado"].dropna()) - set(ESTADOS_EXCEPCION)
    if invalidos:
        raise ValueError(f"excepciones.csv tiene estados inválidos: {sorted(invalidos)}")
    return excepciones


def bloqueantes(tabla: pd.DataFrame, bloque: str, excepciones: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separa los controles que bloquean: devuelve (los que frenan, los cubiertos por una excepción
    aprobada). Una excepción cubre un control solo si está "aprobada" y coinciden bloque, control y alcance."""
    tabla = normalizar_controles(tabla)
    fallan = tabla[tabla["estado"].map(ESTADOS)]
    aprobadas = excepciones[(excepciones["estado"] == "aprobada") & (excepciones["bloque"] == bloque)]
    claves = set(zip(aprobadas["control"], aprobadas["alcance"]))
    cubiertos = fallan.apply(lambda f: (f["control"], f["alcance"]) in claves, axis=1) if len(fallan) else pd.Series(dtype=bool)
    return fallan[~cubiertos] if len(fallan) else fallan, fallan[cubiertos] if len(fallan) else fallan


def verificar_corte(series: dict[str, pd.DataFrame], ultimo_mes_completo: pd.Timestamp) -> None:
    """Impide que un mes posterior al último mes completo de la fuente oficial entre a una serie."""
    for nombre, serie in series.items():
        if len(serie) and serie.index.max() > ultimo_mes_completo:
            raise ValueError(f"{nombre} llega a {serie.index.max():%m/%Y}, después del último mes completo de la "
                             f"fuente oficial ({ultimo_mes_completo:%m/%Y})")


def registrar_corrida(fila: dict, raiz: Path = RAIZ) -> None:
    """Agrega una fila a datos/registros/corridas.csv (solo agrega; nunca reescribe las anteriores)."""
    ruta = Path(raiz) / "datos" / "registros" / "corridas.csv"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([fila]).reindex(columns=COLUMNAS_CORRIDAS).to_csv(ruta, mode="a", header=not ruta.exists(), index=False)
