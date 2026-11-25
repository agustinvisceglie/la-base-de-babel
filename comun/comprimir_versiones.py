"""
Comprime las versiones de crudos guardadas sin comprimir (las anteriores al Paso 3a).

Qué hace, en este orden:
    1. Toma del registro (datos/registros/versiones_crudos.csv) cada versión que no termina en .gz.
       Las copias de versiones/ que no figuran en el registro no se tocan (se informan).
    2. Verifica que el SHA-256 del original sea el registrado.
    3. La comprime a <misma ruta>.gz y verifica que el SHA-256 del contenido descomprimido sea el
       registrado. Si algo no coincide, frena sin tocar el registro ni borrar nada.
    4. Solo si todas verificaron: actualiza la ruta `version` de esas filas del registro (le agrega
       .gz). No cambia ninguna otra columna: hash, fechas y bytes quedan iguales (se controla).
    5. Solo con --borrar-originales (ok de Agustín del 25/11/2026 para las 32 versiones de la SE):
       borra cada original, después de volver a verificar su .gz. Nunca toca las copias "vigentes".

Fuentes: ninguna (trabaja sobre datos/crudos/<organismo>/versiones/).
Genera: las versiones .gz y el registro con las rutas nuevas. Devuelve una tabla con lo hecho.

Uso (desde la raíz del repositorio):
    .venv/Scripts/python -m comun.comprimir_versiones                       comprime y actualiza el registro
    .venv/Scripts/python -m comun.comprimir_versiones --borrar-originales   además borra los originales verificados
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from comun import descargas as d


def comprimir_versiones(borrar_originales: bool = False) -> pd.DataFrame:
    registro = d.leer_registro()
    sin_comprimir = registro[~registro["version"].str.endswith(".gz")]
    filas = []
    for version, grupo in sin_comprimir.groupby("version", sort=True):
        hashes = set(grupo["sha256"])
        if len(hashes) != 1:
            raise RuntimeError(f"{version} figura con más de un hash en el registro: {hashes}")
        esperado = hashes.pop()
        original = d.RAIZ / version
        comprimida = original.with_name(original.name + ".gz")
        if not original.exists():
            raise RuntimeError(f"Falta el original {version}")
        hash_original = d.sha256_de(original)
        if hash_original != esperado:
            raise RuntimeError(f"El original {version} no tiene el hash registrado ({hash_original} vs {esperado})")
        if not comprimida.exists():
            d.comprimir(original, comprimida)
        hash_comprimida = d.sha256_de(comprimida)
        if hash_comprimida != esperado:
            raise RuntimeError(f"{comprimida.name} descomprimido no reproduce el hash registrado")
        filas.append({"version": version, "version_gz": comprimida.relative_to(d.RAIZ).as_posix(), "filas_del_registro": len(grupo),
                      "bytes_original": original.stat().st_size, "bytes_gz": comprimida.stat().st_size,
                      "sha256": esperado, "hash_original_ok": True, "hash_gz_ok": True, "original_borrado": False})
    resultado = pd.DataFrame(filas)
    if resultado.empty:
        return resultado

    # Todas verificaron: se actualizan las rutas del registro y se controla que nada más cambie.
    nuevo = registro.copy()
    nuevo["version"] = nuevo["version"].replace(dict(zip(resultado["version"], resultado["version_gz"])))
    otras = [c for c in d.COLUMNAS_REGISTRO if c != "version"]
    if not nuevo[otras].equals(registro[otras]) or len(nuevo) != len(registro):
        raise RuntimeError("Al actualizar las rutas cambió otra columna del registro: no se escribe")
    temporal = d.REGISTRO_VERSIONES.with_name(d.REGISTRO_VERSIONES.name + ".parcial")
    nuevo.to_csv(temporal, index=False)
    temporal.replace(d.REGISTRO_VERSIONES)

    if borrar_originales:
        for i, fila in resultado.iterrows():
            comprimida = d.RAIZ / fila["version_gz"]
            if comprimida.exists() and d.sha256_de(comprimida) == fila["sha256"]:
                (d.RAIZ / fila["version"]).unlink()
                resultado.loc[i, "original_borrado"] = True
    return resultado


def versiones_fuera_del_registro() -> list[str]:
    """Copias en datos/crudos/*/versiones/ que no figuran en el registro (no se tocan)."""
    registradas = set(d.leer_registro()["version"])
    en_disco = {p.relative_to(d.RAIZ).as_posix() for p in d.CRUDOS.glob("*/versiones/*") if p.is_file()}
    return sorted(en_disco - registradas)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    argumentos = argparse.ArgumentParser(description="Comprime las versiones de crudos sin comprimir.")
    argumentos.add_argument("--borrar-originales", action="store_true",
                            help="borra cada original después de verificar su .gz (requiere el ok de Agustín)")
    tabla = comprimir_versiones(argumentos.parse_args().borrar_originales)
    pd.set_option("display.width", 220)
    if tabla.empty:
        print("No hay versiones sin comprimir en el registro.")
    else:
        print(tabla.drop(columns=["sha256", "version"]).to_string(index=False))
        print(f"\n{len(tabla)} versiones: {tabla['bytes_original'].sum():,} bytes sin comprimir -> {tabla['bytes_gz'].sum():,} "
              f"comprimidas; originales borrados: {int(tabla['original_borrado'].sum())}")
    print("Copias de versiones/ fuera del registro (no se tocan):", versiones_fuera_del_registro())
