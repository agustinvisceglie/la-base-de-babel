"""
Nota "La vuelta del gas". Control del capítulo 27 en la base comex del INDEC vs. cifras oficiales.

Desde el Paso 3b (25/11/2026) este control es parte de la base: lo corre el armador del bloque de
sector externo (bloques/sector_externo/comercio_exterior.py) y queda en
datos/validacion/sector_externo/cap27_comex_vs_oficial.csv. Este script ya no baja nada: solo
muestra ese control, para que correr_todo.py siga funcionando igual.

Fuentes: datos/validacion/sector_externo/cap27_comex_vs_oficial.csv.
Genera: nada.

Uso (desde la raíz del repositorio):
    .venv/Scripts/python notas/2026-12-la-vuelta-del-gas/control_comex.py
"""

import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
CONTROL = RAIZ / "datos" / "validacion" / "sector_externo" / "cap27_comex_vs_oficial.csv"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    tabla = pd.read_csv(CONTROL)
    for fila in tabla.itertuples():
        print(f"{fila.periodo}: expo comex {fila.expo_comex_musd:8.1f} vs oficial {fila.expo_oficial_musd:8.1f} "
              f"({fila.dif_expo_pct:+.1f}%) | impo comex {fila.impo_comex_musd:8.1f} vs oficial {fila.impo_oficial_musd:8.1f}")
    print(f"(control de la base: {CONTROL.relative_to(RAIZ).as_posix()})")


if __name__ == "__main__":
    main()
