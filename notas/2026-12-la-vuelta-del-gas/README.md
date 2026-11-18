# La vuelta del gas

Datos y código de la nota de **El Pozo y el Péndulo** de diciembre de 2026, en [Sobre Modelos y Tumbas](https://sobremodelosytumbas.substack.com).

**Pregunta:** ¿cuánto del saldo comercial de bienes de la Argentina explica hoy la energía, y cuánto de eso es estructural (más producción, Vaca Muerta) y cuánto coyuntural (precios internacionales)?

**Definición del saldo energético:** exportaciones de **Combustibles y energía (CyE)** menos importaciones de **Combustibles y lubricantes (CyL)**, del Intercambio comercial argentino (ICA) del INDEC. Es la cifra que usan la Secretaría de Energía y las consultoras. El capítulo 27 de la Nomenclatura Común del Mercosur queda solo como control (ver `informe_validacion.md`).

**Período:** desde 2004, el comienzo de la serie mensual oficial. **Corte:** septiembre de 2026 (informe del ICA del 19/10/2026).

## Cómo reproducir todo

Desde la raíz del repositorio, con Python 3.12:

```
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt      # en Linux/Mac: .venv/bin/python
.venv/Scripts/python notas/2026-12-la-vuelta-del-gas/correr_todo.py
```

El script baja los datos de las fuentes oficiales del INDEC, arma las series, genera los gráficos y corre los controles; si un control falla, lo dice en pantalla. Los datos se bajan en cada corrida, y la fecha de cada descarga queda en `validacion/`. El mes de corte está fijo en `1_ica.py` (`MES_DE_CORTE`): si el INDEC publica un informe más nuevo, no se usa hasta cambiar el corte.

## Archivos

| Archivo | Qué es |
|---|---|
| `correr_todo.py` | Corre todo en orden. |
| `1_ica.py` | Etapa 1: saldo energético (CyE − CyL) y saldo comercial de bienes; genera g1, g2, las cifras para el texto y los controles. |
| `control_comex.py` | Control del capítulo 27: la base comex del INDEC vs. las cifras oficiales (muestra el efecto del secreto estadístico). |
| `cifras_para_el_texto.csv` | **Las cifras que se citan en la nota**: CyE, CyL, saldo energético y su peso en el saldo comercial de bienes en 2023, 2024, 2025, ene–sep 2025, ene–sep 2026 y últimos 12 meses. Salen solo de anuales y acumulados oficiales. |
| `informe_validacion.md` | Fuentes, definiciones, contraste de cada serie contra lo publicado por el INDEC y por terceros, y el control con el capítulo 27. |
| `graficos/g1_balanza_energetica_anual.csv` | Exportaciones de CyE, importaciones de CyL y saldo por año (2004–2025, anuales oficiales), más ene–sep del año anterior y del año en curso (acumulados oficiales). |
| `graficos/g2_saldo_energetico_vs_total_12m.csv` | Saldo energético (CyE − CyL) y saldo comercial de bienes, suma de 12 meses, mensual desde diciembre de 2004. |
| `graficos/*.png` | Gráficos rápidos para revisar los CSV (no son los de la nota). |
| `validacion/` | Controles y comparaciones: valores leídos vs. publicados, primera publicación vs. dato vigente, referencias publicadas por terceros (−4.470, 5.668, 7.815, 7.834), CyE − CyL vs. capítulo 27, controles del capítulo 27, informes usados y registro de descargas. |

Series limpias que genera la nota, en `datos/procesados/` (se pueden reusar en otras notas):

| Archivo | Qué es |
|---|---|
| `ica_mensual.csv` | Mensual desde 2004: exportaciones e importaciones totales, CyE, CyL, saldo comercial de bienes y saldo CyE − CyL. |
| `ica_anual.csv` | Anual oficial: totales, CyE, CyL y capítulo 27, con la marca de dato provisorio y el cuadro del que sale el capítulo 27. |
| `ica_cap27_mensual.csv` | Capítulo 27 mensual desde 2004, con la fuente de cada mes. Solo para el control. |

Las descargas originales quedan en `datos/crudos/`, que no se sube al repositorio porque se regenera con los scripts.

## Formato de los CSV de gráficos

Punto decimal, coma como separador de columnas y una fila por período, listos para pegar en Datawrapper (que después los muestra con formato argentino). Valores en millones de dólares corrientes; exportaciones FOB, importaciones CIF.

Fuente sugerida para los gráficos: *"Fuente: INDEC, Intercambio comercial argentino. Exportaciones de Combustibles y energía (CyE) menos importaciones de Combustibles y lubricantes (CyL). 2024 y 2025, datos provisorios; 2026, exportaciones estimadas e importaciones provisorias."* (son las marcas del INDEC en los cuadros del informe del 19/10/2026). La serie no tiene valores estimados por nosotros, así que no lleva nota de estimación.

## Estado

- [x] Etapa 1: saldo energético y saldo comercial de bienes (g1, g2)
- [ ] Etapa 2: producción de petróleo y gas (g3)
- [ ] Etapa 3: precios y cantidades (g4)
