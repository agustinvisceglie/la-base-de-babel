# La Base de Babel

Datos, métodos y código de **[Sobre Modelos y Tumbas](https://sobremodelosytumbas.substack.com)**, una publicación sobre macroeconomía y energía argentina.

> *Base*, por base de datos, por el año base de las series y por la base monetaria. *Babel*, por Borges.

## Qué hay acá

Una base de series económicas y energéticas de la Argentina, armadas una sola vez con un comando (`actualizar.py`) a partir de las fuentes oficiales, con sus controles y su catálogo (`catalogo_series.csv`). Cada nota de la publicación tiene su carpeta y lee de esa base, para que cualquiera pueda revisar y reproducir los números.

## Estructura

```
actualizar.py      un comando: baja (si cambió), arma y controla la base; regenera el catálogo
catalogo_series.csv  una fila por serie: fuente, unidad, criterio, inicio, fin, uso y estado de validación
comun/             código común: descargas y versiones, controles, catálogo, respaldo
lectores/          uno por organismo: bajan y leen los archivos tal como los publica la fuente
bloques/           armadores por bloque (sector externo, energía, ...): aplican los criterios y controlan
datos/
  crudos/          versiones comprimidas de cada descarga (no se suben: el hash queda en registros/)
  series/          series limpias por bloque, listas para analizar y graficar
  validacion/      controles e informes de validación por bloque
  registros/       versiones de los crudos, corridas, excepciones, auditorías y respaldos
notas/             una carpeta por nota: lee la base y arma sus gráficos y cifras
tests/             tests de lectores, controles y migración (python -m unittest discover -s tests -v)
requirements.txt   paquetes de Python con sus versiones exactas
```

Para armar la base: `python actualizar.py` (todo), `--bloque energia`, `--sin-descargar` o `--crudos-al AAAA-MM-DD` (con las versiones de los crudos que había ese día).

## Fuentes

Solo datos públicos: INDEC, BCRA, Secretaría de Energía y la API de Series de Tiempo de datos.gob.ar, entre otras. El catálogo indica de dónde sale cada serie, y cada lector y cada armador lo dice en su encabezado.

## Autor

Agustín Visceglie, economista (UBA). [Substack](https://sobremodelosytumbas.substack.com) · [LinkedIn](https://www.linkedin.com/in/agustin-visceglie-6ba3431b5/)

## Licencia

Código bajo licencia MIT. Si usás algo, se agradece la cita.
