# La Base de Babel

Datos, métodos y código de **[Sobre Modelos y Tumbas](https://sobremodelosytumbas.substack.com)**, una publicación sobre macroeconomía y energía argentina.

> *Base*, por base de datos, por el año base de las series y por la base monetaria. *Babel*, por Borges.

## Qué hay acá

Cada nota de la publicación que usa datos tiene su carpeta con el código que baja, procesa y grafica las series, para que cualquiera pueda revisar y reproducir los números.

## Estructura

```
datos/
  crudos/          descargas originales de cada fuente (no se suben: se regeneran con los scripts)
  procesados/      series limpias, listas para analizar y graficar
scripts/           funciones reutilizables de descarga y limpieza, por fuente
notas/             una carpeta por nota publicada, reproducible con un comando
tests/             tests de los lectores de cuadros (python -m unittest discover -s tests -v)
requirements.txt   paquetes de Python con sus versiones exactas
```

## Fuentes

Solo datos públicos: INDEC, BCRA, Secretaría de Energía y la API de Series de Tiempo de datos.gob.ar, entre otras. Cada script indica de dónde sale cada serie.

## Autor

Agustín Visceglie, economista (UBA). [Substack](https://sobremodelosytumbas.substack.com) · [LinkedIn](https://www.linkedin.com/in/agustin-visceglie-6ba3431b5/)

## Licencia

Código bajo licencia MIT. Si usás algo, se agradece la cita.
