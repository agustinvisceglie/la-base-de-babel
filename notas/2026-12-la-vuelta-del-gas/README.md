# La vuelta del gas

Datos y código de la nota de **El Pozo y el Péndulo** de diciembre de 2026, en [Sobre Modelos y Tumbas](https://sobremodelosytumbas.substack.com).

**Pregunta:** ¿cuánto del saldo comercial de bienes de la Argentina explica hoy la energía, y cuánto de eso es estructural (más producción, Vaca Muerta) y cuánto coyuntural (precios internacionales)?

**Definición de energía:** capítulo 27 de la Nomenclatura Común del Mercosur (combustibles minerales, aceites minerales y productos de su destilación), igual para exportaciones e importaciones. Es el saldo energético que publica el INDEC en el informe técnico del Intercambio comercial argentino (ICA).

## Cómo reproducir todo

Desde la raíz del repositorio, con Python 3.12:

```
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt      # en Linux/Mac: .venv/bin/python
.venv/Scripts/python notas/2026-12-la-vuelta-del-gas/correr_todo.py
```

El script baja los datos de las fuentes oficiales del INDEC, rearma las series, genera los gráficos y corre los controles; si un control falla, lo dice en pantalla. Los datos se bajan en cada corrida. Cuando el INDEC publica un informe nuevo, el script lo encuentra solo y cada mes queda con su revisión más reciente. La fecha de cada descarga queda en `validacion/`.

## Archivos

| Archivo | Qué es |
|---|---|
| `correr_todo.py` | Corre todo en orden. |
| `1_ica.py` | Etapa 1: saldo energético (capítulo 27) y saldo comercial de bienes; genera g1, g2 y las cifras para el texto. |
| `control_comex.py` | Control: el capítulo 27 sumado en la base comex del INDEC vs. las cifras oficiales (muestra el efecto del secreto estadístico). |
| `cifras_para_el_texto.csv` | **Las cifras que se citan en la nota**: saldo del capítulo 27 y su peso en el saldo comercial de bienes en 2023, 2024, 2025, ene–sep 2025, ene–sep 2026 y últimos 12 meses. Salen solo de anuales y acumulados oficiales. |
| `informe_validacion.md` | Fuentes, decisiones metodológicas, por qué se usa cada fuente y contraste de cada serie contra lo publicado por el INDEC. |
| `graficos/g1_balanza_energetica_anual.csv` | Exportaciones, importaciones y saldo del capítulo 27 por año (2006–2025, anuales oficiales), más ene–sep del año anterior y del año en curso (acumulados oficiales). |
| `graficos/g2_saldo_energetico_vs_total_12m.csv` | Saldo del capítulo 27 y saldo comercial de bienes, suma de 12 meses, mensual desde enero de 2006. |
| `graficos/*.png` | Gráficos rápidos para revisar los CSV (no son los de la nota). |
| `validacion/` | Controles y comparaciones: valores leídos vs. publicados, suma de meses vs. oficiales, CyE − CyL vs. capítulo 27, base comex vs. oficial, API vs. informes, unidades, informes usados y registro de descargas. |

Series limpias que genera la nota, en `datos/procesados/` (se pueden reusar en otras notas):

| Archivo | Qué es |
|---|---|
| `ica_cap27_mensual.csv` | Capítulo 27 mensual desde 2005: exportaciones, importaciones y saldo, con la fuente de cada mes (informe del INDEC del que sale, o API). |
| `ica_mensual.csv` | Mensual desde 2004: exportaciones e importaciones totales, Combustibles y energía (CyE), Combustibles y lubricantes (CyL), saldo comercial de bienes y saldo CyE − CyL. |
| `ica_anual.csv` | Anual oficial: totales, CyE, CyL y capítulo 27, con la marca de dato provisorio y el cuadro del que sale el capítulo 27. |

Las descargas originales quedan en `datos/crudos/`, que no se sube al repositorio porque se regenera con los scripts.

## Formato de los CSV de gráficos

Punto decimal, coma como separador de columnas y una fila por período, listos para pegar en Datawrapper (que después los muestra con formato argentino). Valores en millones de dólares corrientes; exportaciones FOB, importaciones CIF.

Fuente sugerida para los gráficos: *"Fuente: INDEC, Intercambio comercial argentino (capítulo 27 de la NCM). 2024 y 2025, datos provisorios; 2026, estimados."* En g2 conviene agregar: *"Cada mes, con su última revisión publicada."* La serie no tiene valores estimados por nosotros, así que no lleva nota de estimación.

## Estado

- [x] Etapa 1: saldo energético y saldo comercial de bienes (g1, g2)
- [ ] Etapa 2: producción de petróleo y gas (g3)
- [ ] Etapa 3: precios y cantidades (g4)
