"""
actualizar.py: un comando para bajar, armar y controlar la base y regenerar el catálogo.

Qué hace en cada corrida:
    1. Resuelve qué armadores corren (todos, un bloque o el de una serie, más los que producen las
       series de las que dependen) y en qué orden.
    2. Para cada armador: los lectores bajan y versionan los crudos (salvo --sin-descargar o
       --crudos-al), el armador arma las series y corre los controles.
       - Si un control da REVISAR y no hay una excepción aprobada en datos/registros/excepciones.csv
         (mismo bloque, control y alcance), el armador NO escribe nada: quedan las series anteriores,
         y los armadores que dependen de él no corren. La corrida termina con error.
       - Si no, escribe las series en datos/series/<bloque>/, y los controles y la validación en
         datos/validacion/<bloque>/.
    3. Regenera catalogo_series.csv, verifica que catálogo y series coincidan en los dos sentidos,
       agrega una fila a datos/registros/corridas.csv y muestra un resumen.

Lo que NO hace: no commitea ni hace push (eso sigue con el ok de Agustín). No borra archivos.

Uso (desde la raíz del repositorio):
    .venv/Scripts/python actualizar.py                          todo
    .venv/Scripts/python actualizar.py --bloque energia         un bloque (y lo que necesita de otros)
    .venv/Scripts/python actualizar.py --serie <id>             el armador de esa serie
    .venv/Scripts/python actualizar.py --sin-descargar          rearma con las últimas versiones ya bajadas
    .venv/Scripts/python actualizar.py --crudos-al 2026-10-31   rearma con las versiones publicadas hasta esa fecha
    .venv/Scripts/python actualizar.py --listar                 muestra bloques, armadores, series y dependencias
    .venv/Scripts/python actualizar.py --ok-descarga-grande     ok de Agustín para bajar más de 1 GB (regla 8)

Fuentes: las de cada armador. Genera: datos/series/, datos/validacion/<bloque>/, catalogo_series.csv,
    datos/registros/corridas.csv (y, vía los lectores, versiones de crudos y su registro).
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import pandas as pd

from comun import catalogo, controles, descargas


def argumentos(argv=None) -> argparse.Namespace:
    analizador = argparse.ArgumentParser(description="Baja, arma y controla la base, y regenera el catálogo. No commitea.")
    analizador.add_argument("--bloque", help="solo este bloque (y lo que necesita de otros)")
    analizador.add_argument("--serie", help="solo el armador de esta serie (id del catálogo)")
    analizador.add_argument("--sin-descargar", action="store_true", help="usa las últimas versiones ya bajadas, sin internet")
    analizador.add_argument("--crudos-al", metavar="AAAA-MM-DD", help="usa las versiones de los crudos publicadas hasta esa fecha")
    analizador.add_argument("--listar", action="store_true", help="muestra bloques, armadores, series y dependencias")
    analizador.add_argument("--ok-descarga-grande", action="store_true", help="ok de Agustín para bajar más de 1 GB (regla 8)")
    return analizador.parse_args(argv)


def listar(lista: list[catalogo.Armador]) -> None:
    if not lista:
        print("No hay armadores en bloques/ todavía.")
        return
    for armador in lista:
        print(f"{armador.bloque:<16} {armador.ruta}")
        for serie in armador.series:
            print(f"    {serie['id']}  ({serie['unidad']}, {serie['frecuencia']}, uso {serie['uso']})")
        if armador.depende_de:
            print(f"    depende de: {', '.join(armador.depende_de)}")


def _escribir(armador: catalogo.Armador, resultado: dict, tabla_controles: pd.DataFrame, raiz: Path) -> None:
    for archivo, tabla in resultado["series"].items():
        ruta = catalogo.ruta_serie(armador.bloque, archivo, raiz)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        tabla.to_csv(ruta, float_format=armador.formato.get(archivo), date_format="%Y-%m-%d")
    carpeta = Path(raiz) / "datos" / "validacion" / armador.bloque
    carpeta.mkdir(parents=True, exist_ok=True)
    tabla_controles.to_csv(carpeta / f"{armador.nombre}_controles.csv", index=False)
    for nombre, contenido in resultado.get("validacion", {}).items():
        if isinstance(contenido, pd.DataFrame):
            contenido.to_csv(carpeta / nombre, date_format="%Y-%m-%d")
        else:
            (carpeta / nombre).write_text(str(contenido), encoding="utf-8")


def _control_de_forma(armador: catalogo.Armador, resultado: dict) -> dict:
    """Que el armador devuelva exactamente las series que declara (más sus columnas auxiliares)."""
    declaradas = {(s["archivo"], s["columna"]) for s in armador.series}
    devueltas = set()
    for archivo, tabla in resultado.get("series", {}).items():
        auxiliares = set(armador.auxiliares.get(archivo, []))
        devueltas |= {(archivo, c) for c in tabla.columns if c not in auxiliares}
    faltan, sobran = sorted(declaradas - devueltas), sorted(devueltas - declaradas)
    return {"control": "Las series que devuelve el armador son las que declara (SERIES y AUXILIARES)",
            "estado": "OK" if not faltan and not sobran else "REVISAR",
            "detalle": f"faltan {faltan}; sobran {sobran}" if faltan or sobran else "", "alcance": ""}


def ejecutar(argv=None, lista: list[catalogo.Armador] | None = None, raiz: Path = RAIZ) -> int:
    """Corre actualizar.py. `lista` y `raiz` permiten probarlo con armadores y carpetas de prueba."""
    args = argumentos(argv)
    inicio = datetime.now()
    reloj = time.time()
    lista = catalogo.armadores(raiz) if lista is None else lista
    if args.listar:
        listar(lista)
        return 0

    seleccion = catalogo.resolver(lista, args.bloque, args.serie) if lista else []
    descargas.configurar(args.sin_descargar, args.crudos_al, args.ok_descarga_grande)
    excepciones = controles.leer_excepciones(raiz)
    versiones_antes = len(descargas.leer_registro())

    corridas, frenados, no_corrieron, bloqueantes_txt, cubiertos_txt, a_revisar = {}, [], [], [], [], 0
    for armador in seleccion:
        frenado_por = [d for d in armador.depende_de if any(s["id"] == d for f in frenados for s in f.series)]
        if frenado_por:
            no_corrieron.append(f"{armador.ruta} (depende de {', '.join(frenado_por)}, que frenó)")
            frenados.append(armador)
            continue
        print(f"Armando {armador.ruta}...")
        resultado = armador.modulo.armar()
        tabla = controles.normalizar_controles(pd.concat(
            [resultado["controles"], pd.DataFrame([_control_de_forma(armador, resultado)])], ignore_index=True))
        frenan, cubiertos = controles.bloqueantes(tabla, armador.bloque, excepciones)
        a_revisar += int(tabla["estado"].isin(["REVISAR", "DIFERENCIAS"]).sum())
        cubiertos_txt += [f"{armador.ruta}: {c}" for c in cubiertos["control"]]
        if len(frenan):
            frenados.append(armador)
            bloqueantes_txt += [f"{armador.ruta}: {f.control} [{f.alcance}] {f.detalle}" for f in frenan.itertuples()]
            print(f"    FRENADO: {len(frenan)} control(es) en REVISAR sin excepción aprobada; no se escribe nada.")
            continue
        _escribir(armador, resultado, tabla, raiz)
        corridas[armador.ruta] = catalogo.datos_de_corrida(resultado.get("registros", []), tabla)

    nuevo = catalogo.armar_catalogo(lista, corridas, catalogo.leer_catalogo(raiz), catalogo.leer_auditorias(raiz), raiz)
    catalogo.escribir_catalogo(nuevo, raiz)
    faltan, sobran = catalogo.verificar_catalogo(nuevo, lista, raiz)
    error = bool(frenados) or bool(faltan) or bool(sobran)

    modo = "sin descargar" if args.sin_descargar else (f"crudos al {args.crudos_al}" if args.crudos_al else "normal")
    controles.registrar_corrida({
        "inicio": inicio.strftime("%Y-%m-%d %H:%M:%S"), "fin": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "duracion_segundos": round(time.time() - reloj, 1), "comando": " ".join(["actualizar.py"] + list(sys.argv[1:] if argv is None else argv)),
        "modo": modo, "armadores": "; ".join(a.ruta for a in seleccion), "armadores_escritos": "; ".join(corridas),
        "armadores_frenados": "; ".join([a.ruta for a in frenados]),
        "controles_bloqueantes": " | ".join(bloqueantes_txt), "controles_cubiertos_por_excepcion": " | ".join(cubiertos_txt),
        "controles_a_revisar": a_revisar, "versiones_nuevas_de_crudos": len(descargas.leer_registro()) - versiones_antes,
        "resultado": "error" if error else "ok"}, raiz)

    print(f"\nArmadores: {len(seleccion)}; escritos: {len(corridas)}; frenados: {len(frenados)}. "
          f"Series en el catálogo: {len(nuevo)}. Controles en REVISAR o DIFERENCIAS: {a_revisar}.")
    for linea in bloqueantes_txt + no_corrieron:
        print(f"    frenó: {linea}")
    if faltan or sobran:
        print(f"    catálogo y series no coinciden: faltan en el catálogo {faltan}; sobran {sobran}")
    print("No se commiteó nada.")
    return 1 if error else 0


if __name__ == "__main__":
    sys.exit(ejecutar())
