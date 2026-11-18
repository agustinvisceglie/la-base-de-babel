"""
Reproduce todos los datos de la nota "La vuelta del gas" con un solo comando.

Qué hace: corre, en orden, los scripts de cada etapa. Si una etapa falla, se detiene.
Fuentes: las de cada etapa (ver el encabezado de cada script y el README de esta carpeta).
Genera: todo lo que generan las etapas (datos/procesados/, graficos/ y validacion/).

Uso (desde la raíz del repositorio):
    .venv/Scripts/python notas/2026-12-la-vuelta-del-gas/correr_todo.py
"""

import subprocess
import sys
from pathlib import Path

CARPETA_NOTA = Path(__file__).resolve().parent

# Etapas en el orden en que se corren. Se agregan a medida que se terminan.
ETAPAS = [
    "1_ica.py",                 # saldo energético (CyE - CyL) y saldo comercial de bienes (g1, g2)
    "control_comex.py",         # control: capítulo 27 en la base comex vs. cifras oficiales
]

for etapa in ETAPAS:
    print(f"\n{'=' * 80}\nEtapa: {etapa}\n{'=' * 80}")
    subprocess.run([sys.executable, str(CARPETA_NOTA / etapa)], check=True)

print("\nListo: todas las etapas terminaron sin errores.")
