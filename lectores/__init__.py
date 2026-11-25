"""
Lectores, uno por organismo (por ejemplo, lectores/indec.py o lectores/secretaria_energia.py).

Un lector baja (con comun/descargas.py, versionando) y lee un archivo de la fuente, y lo devuelve como
tabla con las columnas y las unidades de la fuente. No convierte unidades, no agrupa, no suma y no
elige variantes: eso lo hacen los armadores de bloques/. Cada lector tiene tests contra valores
publicados por la fuente. Los lectores actuales (scripts/) se mudan acá en los Pasos 3b y 3c.
"""
