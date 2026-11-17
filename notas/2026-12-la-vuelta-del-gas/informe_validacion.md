# Informe de validación: "La vuelta del gas"

Nota de la sección **El Pozo y el Péndulo** (diciembre de 2026).

**Pregunta de la nota:** ¿cuánto del saldo comercial de bienes de la Argentina explica hoy la energía, y cuánto de eso es estructural (más producción, Vaca Muerta) y cuánto coyuntural (precios internacionales)?

| Etapa | Contenido | Estado |
|---|---|---|
| 1 | Saldo energético (capítulo 27 de la NCM) y saldo comercial de bienes: g1 y g2 | Completa. Última corrida: 17/11/2026 (datos hasta septiembre de 2026, informe ICA del 19/10/2026) |
| 2 | Producción de petróleo y gas (Capítulo IV): g3 | Pendiente |
| 3 | Índices de precios y cantidades: g4 | Pendiente |

Los controles de cada corrida quedan en `validacion/` y se regeneran con `correr_todo.py`. Este informe resume la corrida indicada arriba. Todos los valores están en millones de USD corrientes.

---

## Etapa 1. Saldo energético y saldo comercial de bienes

### Cifras para citar en el texto

Salen **solo de anuales y acumulados oficiales** (no de sumar meses). Archivo: `cifras_para_el_texto.csv`.

| Período | Expo cap. 27 | Impo cap. 27 | Saldo cap. 27 | Saldo comercial de bienes | Peso del saldo cap. 27 |
|---|---:|---:|---:|---:|---:|
| 2023 | 6.563,1 | 7.763,0 | −1.200,0 | −6.860,6 | 17,5% (1) |
| 2024 | 8.239,2 | 3.777,8 | 4.461,4 | 18.927,6 | 23,6% |
| 2025 | 9.717,8 | 3.042,5 | 6.675,3 | 11.320,1 | 59,0% |
| Ene–sep 2025 | 7.074,7 | 2.571,5 | 4.503,2 | 6.046,2 | 74,5% |
| Ene–sep 2026 | 10.786,9 | 2.787,2 | 7.999,6 | 21.198,3 | 37,7% |
| 12 meses a sep-2026 (2) | 13.429,9 | 3.258,3 | 10.171,6 | 26.472,2 | 38,4% |

1. En 2023 los dos saldos son negativos: el déficit energético fue el 17,5% del déficit comercial de bienes. No se lee como "aporte" al saldo.
2. Derivado solo de cifras oficiales: anual 2025 + acumulado ene–sep 2026 − acumulado ene–sep 2025.

Fuentes: anuales, `exp_ncm_21_25.xls` e `imp_ncm_21_25.xls` (capítulo 27), y `exp_gr_80_25.xls` e `imp_uso_econ_80_25.xls` (saldo de bienes). Acumulados, informe ICA del 19/10/2026 (cuadro 8 para el capítulo 27 y cuadro 1 para el saldo de bienes). 2025 es dato provisorio y 2026, estimado.

**Diferencia entre la suma de los meses y el acumulado oficial, ene–sep 2026:** la suma de los meses da 7.874,0 contra 7.999,6 del acumulado oficial (−125,6; −1,6%). Por exportaciones, −236,3; por importaciones, −110,7. El motivo se explica en el control 4. Por eso el último punto de g2 (10.022,8) queda 148,8 por debajo de la cifra oficial de 12 meses (10.171,6). En el texto se cita la cifra oficial.

### Definición: capítulo 27 de la NCM

"Energía" es el capítulo 27 de la Nomenclatura Común del Mercosur (combustibles minerales, aceites minerales y productos de su destilación; materias bituminosas; ceras minerales), con la misma definición para exportaciones e importaciones. Es el saldo energético que publica el INDEC en la sección 3.4 del informe técnico del ICA. Exportaciones FOB, importaciones CIF, dólares corrientes sin deflactar. El saldo analizado es el **saldo comercial de bienes** (ICA), no la cuenta corriente: no incluye servicios ni rentas.

Antes se usaba CyE − CyL (gran rubro de exportación contra uso económico de importación). Se descartó porque mezcla dos clasificaciones distintas y da un saldo más alto: en ene–sep 2026, 9.427,8 contra 7.999,6 (+17,9%). La comparación completa está más abajo.

### Fuentes

| Serie | Archivo o ID | Organismo | Frecuencia | Uso |
|---|---|---|---|---|
| Capítulo 27, expo e impo, mes del informe y mismo mes del año anterior; acumulados | Excel de cuadros de cada informe técnico del ICA (`ica_cuadros_DD_MM_AA.xls`, hoja del capítulo 27: `c8`, o `c7` en enero). 20 informes, del 19/03/2025 al 19/10/2026; lista con URL en `validacion/informes_ica_usados.csv` | INDEC | Mensual | Serie mensual desde 02/2024 y acumulados oficiales |
| Listado de informes técnicos del ICA | [www.indec.gob.ar/Institucional/Indec/InformesTecnicos/40](https://www.indec.gob.ar/Institucional/Indec/InformesTecnicos/40) | INDEC | — | Encontrar cada informe y su Excel de cuadros |
| Capítulo 27, expo e impo | API de Series de Tiempo `162.3_XMB_MINION_0_0_56` y `163.3_MMBUSTIION_0_0_59` | INDEC (publica: Subsecretaría de Programación Macroeconómica) | Mensual, 01/1990–02/2025 | Serie mensual 01/2005–01/2024 y anuales 2006–2009 |
| Capítulo 27, anual | `exp_ncm_AA_AA.xls` e `imp_ncm_AA_AA.xls`, quinquenios del 2010–2014 al 2021–2025 | INDEC | Anual | Anuales 2010–2025 |
| Exportaciones por rubro e importaciones por uso, totales | `exp_gr_80_25.xls`, `imp_uso_econ_80_25.xls` (vienen en miles de USD y se pasan a millones) | INDEC | Anual | Saldo comercial de bienes anual; CyE y CyL anual |
| Exportaciones por rubro e importaciones por uso, mensual desde 2004 | `serie_rubros_usos_mensual.xlsx` de la [versión interactiva del informe](https://www.indec.gob.ar/ftp/ica_digital/ica_d_10_263F42E3F39F/) (viene en USD y se pasa a millones) | INDEC | Mensual | Saldo comercial de bienes mensual (g2); CyE y CyL para la comparación |
| Cuadro 1 del informe (acumulado del año) | Excel de cuadros del último informe | INDEC | Acumulado | Saldo comercial de bienes acumulado |
| Base de comercio exterior por posición NCM | `exports_AAAA_M.zip`, `imports_AAAA_M.zip` en [comex.indec.gob.ar](https://comex.indec.gob.ar/) | INDEC | Mensual | Solo control (ver más abajo) |

Fecha de descarga de todo: **17/11/2026**. La URL, la hora, el tamaño y el hash SHA-256 de cada archivo están en `validacion/descargas.csv` y `validacion/descargas_comex.csv`.

### Cómo se arma cada serie

1. **Capítulo 27 mensual: cada mes con la revisión más reciente publicada.** Cada informe técnico trae el mes del informe (primera publicación) y el mismo mes del año anterior (revisado). El script lee todos los informes publicados desde que la API dejó de actualizarse. Para cada mes se queda con el informe más nuevo que lo publica; por ejemplo, marzo–septiembre de 2025 salen de la columna "2025*" de los informes de 2026. **Cuando sale un informe nuevo, su columna del año anterior reemplaza sola la versión vieja de ese mes.** Los meses que ningún informe cubre salen de la API: hoy, 01/2005–01/2024 (229 meses), y 02/2024–09/2026 (32 meses) sale de informes. La columna `fuente` de `datos/procesados/ica_cap27_mensual.csv` dice de qué informe sale cada mes.
2. **No hay valores estimados.** Todos los meses son cifras publicadas por el INDEC, así que no se agregó columna de estimación ni nota al pie. La regla del `CLAUDE.md` sobre estimaciones no se aplica en esta etapa.
3. **Los meses mezclan revisiones de distinta fecha.** Los meses del año en curso están en su primera publicación hasta que salga el informe del mismo mes del año siguiente. Por eso la suma de los meses no coincide exactamente con los acumulados oficiales (control 4).
4. **Capítulo 27 anual:** para cada año se toma el cuadro anual por capítulo más reciente que lo trae (por ejemplo, 2023 de `21_25` y no de `19_23`). Para 2006–2009 no hay cuadro anual por capítulo publicado, así que se usa la suma de los 12 meses de la API. Antes de 2018 la base de comercio exterior no tenía secreto estadístico y la API coincide exactamente con ella (en 2006, 7.110,6 en las dos).
5. **2025: se usa el anual revisado, 6.675,3** (`exp_ncm_21_25.xls` e `imp_ncm_21_25.xls`: 9.717,8 − 3.042,5). El informe de enero de 2026 (datos de diciembre de 2025, publicado el 20/01/2026) informó un acumulado ene–dic 2025 de **6.663** (6.662,9 en su Excel de cuadros); el INDEC lo revisó después en +12,4.
6. **Saldo comercial de bienes mensual:** sale de `serie_rubros_usos_mensual.xlsx` (suma de todos los rubros y de todos los usos, incluido "Resto"). Reemplaza a la API usada en la versión anterior de esta etapa. Esta serie coincide con los anuales oficiales en todos los años 2004–2025 (diferencia máxima: 0,002) y con el acumulado del cuadro 1. La API, en cambio, no tenía las revisiones de 2014–2016 y 2022–2023.
7. **g1:** años 2006–2025 con los anuales oficiales; ene–sep 2025 y ene–sep 2026 con los acumulados del último informe. El acumulado del año en curso solo se compara con el mismo período del año anterior.
8. **g2:** suma móvil de 12 meses de las series mensuales, desde enero de 2006 (por eso se bajan datos desde 2005).
9. **Datos provisorios:** 2024 y 2025 son provisorios y 2026 es estimado. Las exportaciones de gas por gasoducto de los últimos meses son estimaciones del INDEC hasta que llega el dato final (nota 1 del cuadro 8).

### Por qué esta es la fuente principal

**a) Contra CyE − CyL.** El saldo CyE − CyL supera al del capítulo 27 todos los años, entre 390 y 1.604 millones. La diferencia viene sobre todo de exportaciones: CyE supera a las exportaciones del capítulo 27 en entre 602 y 2.004 millones por año. Archivo: `validacion/comparacion_cye_cyl_vs_cap27.csv`. CyE y CyL salen de `serie_rubros_usos_mensual.xlsx` y de los anuales oficiales por rubro y uso.

| Período | Saldo CyE − CyL | Saldo cap. 27 | Diferencia saldo | Diferencia expo (CyE − cap. 27) | Diferencia impo (CyL − cap. 27) |
|---|---:|---:|---:|---:|---:|
| 2006 | 6.080,8 | 5.506,3 | 574,6 | 702,4 | 127,9 |
| 2007 | 4.104,3 | 3.419,5 | 684,7 | 837,6 | 152,9 |
| 2008 | 3.514,5 | 2.428,3 | 1.086,2 | 1.286,3 | 200,1 |
| 2009 | 3.830,4 | 3.223,2 | 607,2 | 797,0 | 189,8 |
| 2010 | 1.759,9 | 909,0 | 850,9 | 1.137,2 | 286,2 |
| 2011 | −3.114,5 | −4.446,0 | 1.331,5 | 1.725,7 | 394,2 |
| 2012 | −2.150,3 | −3.754,0 | 1.603,7 | 1.996,0 | 392,3 |
| 2013 | −6.902,5 | −8.459,0 | 1.556,5 | 2.003,6 | 447,1 |
| 2014 | −6.400,6 | −7.679,0 | 1.278,4 | 1.741,6 | 463,2 |
| 2015 | −4.608,4 | −5.140,0 | 531,6 | 803,6 | 272,1 |
| 2016 | −2.807,6 | −3.198,0 | 390,4 | 602,0 | 211,7 |
| 2017 | −3.244,2 | −3.812,0 | 567,8 | 811,5 | 243,7 |
| 2018 | −2.354,3 | −3.126,0 | 771,7 | 1.030,2 | 258,5 |
| 2019 | −24,7 | −1.003,0 | 978,3 | 1.234,6 | 256,2 |
| 2020 | 952,9 | 146,0 | 806,8 | 881,0 | 74,2 |
| 2021 | −559,6 | −1.354,3 | 794,7 | 835,0 | 40,3 |
| 2022 | −4.386,4 | −5.875,8 | 1.489,3 | 1.544,3 | 54,9 |
| 2023 | 41,0 | −1.200,0 | 1.240,9 | 1.364,5 | 123,6 |
| 2024 | 5.730,0 | 4.461,4 | 1.268,6 | 1.477,9 | 209,3 |
| 2025 | 7.829,1 | 6.675,3 | 1.153,8 | 1.382,4 | 228,6 |
| Ene–sep 2025 | 5.359,1 | 4.503,2 | 855,9 | 1.031,3 | 175,4 |
| Ene–sep 2026 | 9.427,8 | 7.999,6 | 1.428,2 | 1.665,4 | 237,3 |

El caso que más cambia la lectura es 2023: con CyE − CyL el saldo energético está en equilibrio (+41); con el capítulo 27, en déficit (−1.200).

**b) Contra la base de comercio exterior (comex).** La base de microdatos del INDEC permite sumar el capítulo 27 mes a mes, pero desde 2018 el secreto estadístico tapa parte de las exportaciones. Las posiciones con pocos operadores, como la energía eléctrica, van al código "Confidencial". Las importaciones no tienen ese problema. Archivo: `validacion/cap27_comex_vs_oficial.csv` (lo genera `control_comex.py`).

| Período | Expo comex | Expo oficial | Diferencia | Impo comex | Impo oficial |
|---|---:|---:|---:|---:|---:|
| 2006 (1) | 7.110,6 | 7.110,6 | 0,0% | 1.604,3 | 1.604,3 |
| 2015 | 1.442,0 | 1.442,0 | 0,0% | 6.581,6 | 6.582,0 |
| 2018 | 2.454,0 | 3.171,0 | −22,6% | 6.297,3 | 6.297,0 |
| 2020 | 2.107,8 | 2.712,2 | −22,3% | 2.566,1 | 2.566,1 |
| 2022 | 6.514,0 | 7.044,7 | −7,5% | 12.920,5 | 12.920,5 |
| 2024 | 7.834,7 | 8.239,2 | −4,9% | 3.777,8 | 3.777,8 |
| 2025 | 9.261,1 | 9.717,8 | −4,7% | 3.042,5 | 3.042,5 |
| Ene–sep 2026 | 10.314,3 | 10.786,9 | −4,4% | 2.787,2 | 2.787,2 |

(1) En 2006 la referencia es la suma de la API (no hay cuadro anual por capítulo).

**c) Contra la API sola.** La API trae el total completo del capítulo 27, pero dejó de actualizarse en febrero de 2025. En los 13 meses en que coincide con los informes (02/2024–02/2025), las diferencias son de revisión: como máximo 20,4 en exportaciones y 11,8 en importaciones (`validacion/cap27_api_vs_informes.csv`).

**d) La versión interactiva del informe no tiene la serie del capítulo 27.** La nota "serie original desde 1986, desestacionalizada y tendencia-ciclo desde 1996, con descarga en xlsx" (p. 4 de los informes) se refiere a las exportaciones, importaciones y saldo totales. Revisé las cinco páginas del sitio interactivo y los archivos que cargan sus gráficos: no hay ninguno del capítulo 27.

### Controles

**Control 1. Lo que leemos de los Excel de cuadros vs. lo publicado en los informes** (`validacion/control_valores_publicados.csv`). Los informes redondean a millones enteros; la tolerancia es 1.

| Dato | Leído | Publicado | Diferencia | Estado | Dónde |
|---|---:|---:|---:|---|---|
| Saldo cap. 27, acum. ene–dic 2025 (versión de enero 2026) | 6.662,94 | 6.663 | −0,06 | OK | Informe del 20/01/2026 |
| Saldo cap. 27, acum. ene–ago 2026 | 6.576,25 | 6.576 | 0,25 | OK | Informe del 18/09/2026, p. 28, cuadro 8 |
| Exportación cap. 27, sep-2026 | 1.586,24 | 1.586 | 0,24 | OK | Informe del 19/10/2026, p. 28, cuadro 8 |
| Importación cap. 27, sep-2026 | 145,72 | 146 | −0,28 | OK | Ídem |
| Saldo cap. 27, sep-2026 | 1.440,51 | 1.441 | −0,49 | OK | Ídem |
| Saldo cap. 27, sep-2025 (revisado) | 691,60 | 692 | −0,40 | OK | Ídem |
| Exportación cap. 27, acum. ene–sep 2026 | 10.786,87 | 10.787 | −0,13 | OK | Ídem |
| Importación cap. 27, acum. ene–sep 2026 | 2.787,25 | 2.787 | 0,25 | OK | Ídem |
| Saldo cap. 27, acum. ene–sep 2026 | 7.999,62 | 8.000 | −0,38 | OK | Ídem |
| Saldo cap. 27, acum. ene–sep 2025 (revisado) | 4.503,25 | 4.503 | 0,25 | OK | Ídem |
| Exportaciones totales, acum. ene–sep 2026 | 77.267,05 | 77.267 | 0,05 | OK | Informe del 19/10/2026, p. 7, cuadro 1 |
| Importaciones totales, acum. ene–sep 2026 | 56.068,79 | 56.069 | −0,21 | OK | Ídem |
| Saldo comercial de bienes, acum. ene–sep 2026 | 21.198,25 | 21.198 | 0,25 | OK | Ídem |
| Saldo comercial de bienes, acum. ene–sep 2025 | 6.046,17 | 6.046 | 0,17 | OK | Ídem |

**Control 2. Controles internos** (`validacion/controles.csv`). Todos dan OK:
- Las series mensuales del capítulo 27 (01/2005–09/2026) y de rubros y usos (01/2004–09/2026) no tienen meses faltantes.
- En los 40 cuadros leídos (mes actual y mes del año anterior de 20 informes), el saldo es igual a expo − impo.
- Todos los meses cumplen 0 ≤ capítulo 27 ≤ total, en exportaciones y en importaciones.
- La serie de rubros y usos coincide con los anuales oficiales (2004–2025) y con el acumulado del cuadro 1 (ene–sep 2025 y 2026).

**Control 3. Unidades** (`validacion/control_unidades_cuadros_capitulos.csv`). Uno de los cuadros por capítulo (`exp_ncm_18_22.xls`) no declara la unidad. Por eso, para cada cuadro y año, el total del cuadro se divide por el total anual oficial en millones. Los cocientes van de 0,988 a 1,052: todos están en millones, y las diferencias son revisiones. La mayor, el 2014 estimado del cuadro 2010–2014, no se usa.

**Control 4. Suma de los meses vs. anuales y acumulados oficiales** (`validacion/cap27_suma_meses_vs_oficial.csv`). Mide cuánto pesa la mezcla de revisiones en la serie mensual.

Acumulados de 2026 de cada informe contra la suma de los meses actuales (saldo):

| Acumulado | Informe | Suma de meses | Oficial | Diferencia |
|---|---|---:|---:|---:|
| Ene–feb 2026 | 19/03/2026 | 883,7 | 1.035,9 | −152,2 |
| Ene–mar 2026 | 20/04/2026 | 1.828,9 | 2.008,7 | −179,8 |
| Ene–abr 2026 | 20/05/2026 | 3.077,0 | 3.281,2 | −204,2 |
| Ene–may 2026 | 18/06/2026 | 4.472,4 | 4.686,3 | −213,8 |
| Ene–jun 2026 | 20/07/2026 | 4.940,8 | 5.076,2 | −135,5 |
| Ene–jul 2026 | 20/08/2026 | 5.662,8 | 5.805,8 | −142,9 |
| Ene–ago 2026 | 18/09/2026 | 6.433,5 | 6.576,2 | −142,8 |
| Ene–sep 2026 | 19/10/2026 | 7.874,0 | 7.999,6 | −125,6 |

La mayor parte aparece ya en el informe de febrero. Su acumulado ene–feb implica que el saldo de enero de 2026 fue revisado hacia arriba en unos 152 millones, casi todo por exportaciones (138,6 de esos 152,2). Ese enero revisado no se publica como dato mensual hasta el informe de enero de 2027 (columna "2026*"); cuando salga, el script lo va a tomar solo. Mientras tanto, las cifras para el texto usan los acumulados oficiales. En ene–sep 2025, cuyos meses ya salen revisados, la suma coincide con el acumulado oficial (4.503,2).

Años completos: la suma de los meses difiere del anual oficial en menos de 60 millones por año: 2016 (−56,0), 2021 (−53,2), 2019 (−29,8), 2018 (+26,0), 2025 (−23,2), 2023 (−17,7), 2022 (+16,1), 2024 (−9,9) y 2017 (−1,7). Son revisiones posteriores del INDEC que no se publican mes a mes.

### Lectura rápida de los resultados (para chequear que tengan sentido, no para publicar)

- Saldo del capítulo 27: superávit entre 2006 y 2010; déficit entre 2011 y 2019, con un máximo de −8.459 en 2013; casi equilibrio en 2020 (+146); déficit en 2021 (−1.354), 2022 (−5.876) y 2023 (−1.200); superávit de 4.461 en 2024, 6.675 en 2025 y 7.999,6 en ene–sep 2026 (contra 4.503 en ene–sep 2025).
- Últimos 12 meses a septiembre de 2026 (cifra oficial derivada): saldo energético de 10.171,6, el 38,4% del saldo comercial de bienes (26.472,2).
