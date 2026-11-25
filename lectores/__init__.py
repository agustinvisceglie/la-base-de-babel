"""
Lectores, uno por organismo (por ejemplo, lectores/indec.py o lectores/secretaria_energia.py).

Un lector baja (con comun/descargas.py, versionando) y lee un archivo de la fuente, y lo devuelve como
tabla con las columnas y las unidades de la fuente. No convierte unidades, no agrupa, no suma y no
elige variantes: eso lo hacen los armadores de bloques/. Cada lector tiene tests contra valores
publicados por la fuente. Hoy: indec.py, indec_comex.py, api_series_tiempo.py y secretaria_energia.py.
"""
