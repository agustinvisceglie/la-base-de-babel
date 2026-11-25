# Informe de validación: "La vuelta del gas"

> **Histórico (estado al 18/11/2026).** Desde el Paso 3b (25/11/2026) las series, sus controles y su validación están en la base: `datos/series/sector_externo/`, `datos/series/energia/` y `datos/validacion/sector_externo/informe_validacion.md`. Las rutas `datos/procesados/` de este informe ya no existen (los archivos se mudaron a `datos/series/sector_externo/`). Este informe queda como registro de la nota, que está en pausa (ver README).

Nota de la sección **El Pozo y el Péndulo** (diciembre de 2026).

**Pregunta de la nota:** ¿cuánto del saldo comercial de bienes de la Argentina explica hoy la energía, y cuánto de eso es estructural (más producción, Vaca Muerta) y cuánto coyuntural (precios internacionales)?

| Etapa | Contenido | Estado |
|---|---|---|
| 1 | Saldo energético (CyE − CyL) y saldo comercial de bienes: g1 y g2 | Completa. Última corrida: 18/11/2026 (corte en septiembre de 2026, informe ICA del 19/10/2026) |
| 2 | Producción de petróleo y gas (Capítulo IV): g3 | Pendiente |
| 3 | Índices de precios y cantidades: g4 | Pendiente |

Los controles de cada corrida quedan en `validacion/` y se regeneran con `correr_todo.py`. Este informe resume la corrida indicada arriba. Todos los valores están en millones de USD corrientes, sin deflactar.

---

## Etapa 1. Saldo energético y saldo comercial de bienes

### Definición

- **Saldo energético** = exportaciones del gran rubro **Combustibles y energía (CyE)** − importaciones del uso económico **Combustibles y lubricantes (CyL)**, del Intercambio comercial argentino (ICA) del INDEC. Es la cifra que usan la Secretaría de Energía, IARAF, Economía & Energía y RICSA (criterio validado en el chat del proyecto; ver `criterios-metodologicos.md`).
- Exportaciones FOB, importaciones CIF.
- El saldo de referencia es el **saldo comercial de bienes** del ICA, no la cuenta corriente: no incluye servicios ni rentas.
- **Período:** desde 2004, el comienzo de la serie mensual oficial por rubros y usos.
- **Corte:** septiembre de 2026 (`MES_DE_CORTE` en `1_ica.py`). Si el INDEC publica un informe más nuevo, no se usa hasta cambiar el corte.
- El capítulo 27 de la NCM queda solo como control (última sección de esta etapa).

### Cifras para citar en el texto

Salen **solo de anuales y acumulados oficiales**, no de sumar meses. Archivo: `cifras_para_el_texto.csv`.

| Período | Expo CyE | Impo CyL | Saldo energético | Saldo comercial de bienes | Peso del saldo energético |
|---|---:|---:|---:|---:|---:|
| 2023 | 7.927,6 | 7.886,6 | 41,0 | −6.860,6 | no aplica (1) |
| 2024 | 9.717,1 | 3.987,1 | 5.730,0 | 18.927,6 | 30,3% |
| 2025 | 11.100,2 | 3.271,1 | 7.829,1 | 11.320,1 | 69,2% |
| Ene–sep 2025 | 8.106,0 | 2.746,9 | 5.359,1 | 6.046,2 | 88,6% |
| Ene–sep 2026 | 12.452,3 | 3.024,5 | 9.427,8 | 21.198,3 | 44,5% |
| 12 meses a sep-2026 (2) | 15.446,5 | 3.548,7 | 11.897,7 | 26.472,2 | 44,9% |

1. En 2023 los saldos tienen signos distintos: el energético es positivo (+41,0, dato vigente) y el de bienes, negativo. El cociente no es un peso, así que en el CSV la celda queda vacía y la columna `nota` lo dice. Además, el signo del saldo energético de 2023 cambió con las revisiones del INDEC (ver "Historial de 2023").
2. Derivado solo de cifras oficiales: anual 2025 + acumulado ene–sep 2026 − acumulado ene–sep 2025. Coincide exactamente (diferencia 0,0) con la suma de los últimos 12 meses de la serie mensual (último punto de g2).

**Dato provisorio o estimado:** 2024 y 2025 son provisorios (marca * en los cuadros anuales). En el informe del 19/10/2026, las exportaciones de 2026 figuran como estimadas (2026e) y las importaciones como provisorias (2026*). Son marcas del INDEC; no hay valores estimados por nosotros.

**Origen de cada cifra:**

| Período | Exportaciones (CyE y total) | Importaciones (CyL y total) |
|---|---|---|
| 2023 | [`exp_gr_80_25.xls`](https://www.indec.gob.ar/ftp/cuadros/economia/exp_gr_80_25.xls), hoja "grandes rubros": CyE en I52 (7.927.627,2 miles), total en I48 | [`imp_uso_econ_80_25.xls`](https://www.indec.gob.ar/ftp/cuadros/economia/imp_uso_econ_80_25.xls), hoja "Usos": CyL en I61 (7.886.633,6 miles), total en I58 |
| 2024 | Ídem, J52 y J48 | Ídem, J61 y J58 |
| 2025 | Ídem, B62 y B58 | Ídem, B74 y B71 |
| Ene–sep 2025 y 2026 | [`ica_cuadros_19_10_26.xls`](https://www.indec.gob.ar/ftp/cuadros/economia/ica_cuadros_19_10_26.xls), hoja c12 (Cuadro 12), fila "Combustibles y energía (CyE)", columnas G (2026) y H (2025) | Ídem, hoja c14 (Cuadro 14), fila "Combustibles y lubricantes", columnas G y H |
| Saldo de bienes, ene–sep | Ídem, cuadro 1 (hoja c1) | |

Los cuadros anuales vienen en miles de USD y se pasan a millones.

### Contraste con las cifras publicadas

Los valores de referencia son los validados en el chat del proyecto (`criterios-metodologicos.md` y `auditoria-etapa-1-ica.md`). Para cada uno se buscó la **primera publicación del INDEC** de ese período: tiene que coincidir, salvo redondeo. La diferencia con el **dato vigente** son revisiones posteriores del INDEC. Archivo: `validacion/cye_cyl_vs_referencias_publicadas.csv`.

| Período | Referencia publicada | Publicada por | Primera publicación del INDEC | Dato vigente | Vigente − primera publicación | Expo CyE | Impo CyL |
|---|---:|---|---|---:|---:|---:|---:|
| 2022 | −4.470 (CyE 8.398; CyL 12.868) | IAE Mosconi y Más Energía | −4.470,0 (informe ICA del 19/01/2023, cuadros 4 y 6: CyE 8.398; CyL 12.868) | −4.386,4 | +83,6 | +191,0 | +107,4 |
| 2024 | 5.668 | Secretaría de Energía | 5.667,8 (informe ICA del 20/01/2025, cuadros 4 y 6) | 5.730,0 | +62,2 | +40,5 | −21,7 |
| 2025 | 7.815 | IARAF (N. Argañaraz) | 7.815,1 (informe ICA del 20/01/2026, cuadros 12 y 14) | 7.829,1 | +14,0 | +14,0 | 0,0 |
| Ene–ago 2026 | 7.834 | Economía & Energía (N. Arceo) y RICSA | 7.834,5 (informe ICA del 18/09/2026, cuadros 12 y 14) | 7.827,9 (1) | −6,6 | +4,0 | +10,6 |

1. Suma de enero a agosto de la serie mensual del informe del corte. Es un control: no se cita.

- **Las cuatro referencias coinciden con la primera publicación del INDEC** (diferencias de 0,0, −0,2, +0,1 y +0,5, por redondeo). En 2022 coinciden también los dos componentes.
- **2022:** el saldo vigente es 83,6 menos negativo que el publicado en enero de 2023. Se revisaron hacia arriba los dos componentes: CyE en +191,0 (a 8.589,0) y CyL en +107,4 (a 12.975,4). La revisión de un año después (informe del 18/01/2024) ya había subido CyE a 8.509 y dejaba CyL en 12.868 (saldo −4.359); la de CyL llegó después.
- **2024:** el INDEC revisó el año en el informe del 20/01/2026, que ya trae 5.730,0. Es el valor vigente.
- **2025:** el anual vigente (`exp_gr_80_25.xls`) supera en 14,0 a lo publicado en enero de 2026, todo por exportaciones. Es el caso que menciona `criterios-metodologicos.md` (7.815 contra 7.829). La versión revisada un año después sale en enero de 2027.
- Los informes usados son [`ica_cuadros_19_01_23.xls`](https://www.indec.gob.ar/ftp/cuadros/economia/ica_cuadros_19_01_23.xls), [`ica_cuadros_20_01_25.xls`](https://www.indec.gob.ar/ftp/cuadros/economia/ica_cuadros_20_01_25.xls), [`ica_cuadros_20_01_26.xls`](https://www.indec.gob.ar/ftp/cuadros/economia/ica_cuadros_20_01_26.xls) y [`ica_cuadros_18_09_26.xls`](https://www.indec.gob.ar/ftp/cuadros/economia/ica_cuadros_18_09_26.xls).

### Historial de 2023 (cambio de signo)

Archivo: `validacion/cye_cyl_anual_vs_informes.csv`.

| Versión | Fuente | Expo CyE | Impo CyL | Saldo |
|---|---|---:|---:|---:|
| Primera publicación | Informe ICA del 18/01/2024 ([`ica_cuadros_18_01_24.xls`](https://www.indec.gob.ar/ftp/cuadros/economia/ica_cuadros_18_01_24.xls), cuadros 3 y 5; valores redondeados a millones) | 7.878,0 | 7.924,0 | −46,0 |
| Revisada un año después | Informe ICA del 20/01/2025 (cuadros 4 y 6) | 7.910,7 | 7.924,0 | −13,4 |
| Vigente | `exp_gr_80_25.xls` e `imp_uso_econ_80_25.xls` | 7.927,6 | 7.886,6 | +41,0 |

Las dos primeras versiones dan un déficit chico; la vigente, un superávit chico. En cualquiera de las tres el saldo energético de 2023 está cerca del equilibrio (entre −46 y +41). Con el capítulo 27, en cambio, 2023 es un déficit de −1.200,0.

### Fuentes

| Serie | Archivo o ID | Organismo | Frecuencia | Uso |
|---|---|---|---|---|
| Exportaciones por grandes rubros e importaciones por usos económicos, mensual desde 2004 | [`serie_rubros_usos_mensual.xlsx`](https://www.indec.gob.ar/ftp/ica_digital/ica_d_10_263F42E3F39F/data/cuadros/serie_rubros_usos_mensual.xlsx), de la versión interactiva del informe del 19/10/2026 (viene en USD y se pasa a millones) | INDEC | Mensual | Serie mensual de CyE, CyL y totales (g2) |
| Exportaciones por rubro e importaciones por uso, anual | `exp_gr_80_25.xls`, `imp_uso_econ_80_25.xls` (miles de USD) | INDEC | Anual | Anuales de CyE, CyL y saldo de bienes (g1 y cifras para citar) |
| Excel de cuadros de cada informe técnico del ICA | `ica_cuadros_DD_MM_AA.xls`; lista con URL en `validacion/informes_ica_usados.csv` | INDEC | Mensual | Acumulados oficiales (informe del corte) y primeras publicaciones (informes de enero y de agosto de 2026) |
| PDF del informe técnico del ICA de septiembre de 2026 | [`ica_10_263F42E3F39F.pdf`](https://www.indec.gob.ar/uploads/informesdeprensa/ica_10_263F42E3F39F.pdf) | INDEC | — | Contraste de lo leído con lo publicado (control 1) |
| Listado de informes técnicos del ICA | [www.indec.gob.ar/Institucional/Indec/InformesTecnicos/40](https://www.indec.gob.ar/Institucional/Indec/InformesTecnicos/40) | INDEC | — | Encontrar cada informe y su Excel de cuadros |

Fecha de descarga de todo: **18/11/2026**. Los archivos son idénticos a los de la corrida del 17/11/2026: tienen el mismo hash SHA-256. La URL, la hora, el tamaño y el hash de cada archivo están en `validacion/descargas.csv` y `validacion/descargas_comex.csv`.

### Cómo se arma cada serie

1. **Mensual:** `serie_rubros_usos_mensual.xlsx` viene en formato largo (año, mes, flujo, rubro o uso, valor en USD).
   - CyE es el rubro "Combustibles y energía" y CyL, el uso "Combustibles y lubricantes".
   - Los totales son la suma de todos los rubros o usos, incluido "Resto".
   - **No se derivan ni se estiman meses.**
2. **Anual:** cuadros anuales por rubro y uso. La suma de los 12 meses de la serie mensual coincide con ellos en todos los años 2004–2025: la diferencia máxima es 0,002.
3. **g1:** años 2004–2025 con los anuales oficiales, más ene–sep 2025 y ene–sep 2026 con los acumulados del informe del corte. El acumulado del año en curso solo se compara con el mismo período del año anterior.
4. **g2:** suma móvil de 12 meses de la serie mensual. El primer punto es diciembre de 2004, porque la serie empieza en enero de 2004.
5. **12 meses a septiembre de 2026:** sale de cifras oficiales (anual 2025 + ene–sep 2026 − ene–sep 2025) y coincide exactamente con el último punto de g2.

### Controles

**Control 1. Lo que leemos de los Excel de cuadros vs. lo publicado en el PDF del informe del 19/10/2026** (`validacion/control_valores_publicados.csv`). Los informes redondean a millones enteros; la tolerancia es 1.

| Dato | Leído | Publicado | Diferencia | Estado | Dónde |
|---|---:|---:|---:|---|---|
| Exportación CyE, sep-2026 | 1.781,38 | 1.781 | 0,38 | OK | p. 9 (texto: "USD 1.781 millones") |
| Exportación CyE, acum. ene–sep 2026 | 12.452,34 | 12.452 | 0,34 | OK | p. 6 (gráfico de grandes rubros y usos económicos, acumulado) |
| Importación CyL, acum. ene–sep 2026 | 3.024,54 | 3.025 | −0,46 | OK | p. 6 |
| Exportaciones totales, acum. ene–sep 2026 | 77.267,05 | 77.267 | 0,05 | OK | p. 7, cuadro 1 |
| Importaciones totales, acum. ene–sep 2026 | 56.068,79 | 56.069 | −0,21 | OK | p. 7, cuadro 1 |
| Saldo comercial de bienes, acum. ene–sep 2026 | 21.198,25 | 21.198 | 0,25 | OK | p. 7, cuadro 1 |
| Saldo comercial de bienes, acum. ene–sep 2025 | 6.046,17 | 6.046 | 0,17 | OK | p. 7, cuadro 1 |

El PDF se leyó por texto (con `pypdf`, fuera del repositorio). El archivo también tiene 10 controles del capítulo 27, todos OK.

**Control 2. Controles internos** (`validacion/controles.csv`). Todos dan OK:
- La serie mensual va de enero de 2004 a septiembre de 2026, sin meses faltantes.
- Todos los meses cumplen 0 ≤ CyE ≤ exportaciones totales y 0 ≤ CyL ≤ importaciones totales.
- La serie mensual coincide con los anuales oficiales (2004–2025) y con los acumulados del informe del corte (ene–sep 2025 y 2026): totales contra el cuadro 1 y CyE y CyL contra los cuadros 12 y 14. Las diferencias son de 0,000.
- En el informe del corte, los totales de los cuadros 12 y 14 coinciden con el cuadro 1.
- El acumulado de 12 meses derivado de oficiales coincide con el último punto de g2.
- Las cuatro referencias publicadas coinciden con la primera publicación del INDEC.
- En cada informe usado, el cuadro 1, el de rubros y usos y el del capítulo 27 son del mismo mes.

**Control 3. Anual vigente vs. informes de diciembre** (`validacion/cye_cyl_anual_vs_informes.csv`). Diferencias de vigente menos informe:

| Año | Versión | Informe | Saldo del informe | Saldo vigente | Dif. expo CyE | Dif. impo CyL | Dif. saldo |
|---|---|---|---:|---:|---:|---:|---:|
| 2022 | Primera publicación | 19/01/2023 | −4.470,0 | −4.386,4 | 191,0 | 107,4 | 83,6 |
| 2022 | Revisada | 18/01/2024 | −4.359,0 | −4.386,4 | 80,0 | 107,4 | −27,4 |
| 2023 | Primera publicación | 18/01/2024 | −46,0 | 41,0 | 49,6 | −37,4 | 87,0 |
| 2023 | Revisada | 20/01/2025 | −13,4 | 41,0 | 17,0 | −37,4 | 54,4 |
| 2024 | Primera publicación | 20/01/2025 | 5.667,8 | 5.730,0 | 40,5 | −21,7 | 62,2 |
| 2024 | Revisada | 20/01/2026 | 5.730,0 | 5.730,0 | 0,0 | 0,0 | 0,0 |
| 2025 | Primera publicación | 20/01/2026 | 7.815,1 | 7.829,1 | 14,0 | 0,0 | 14,0 |
| 2025 | Revisada | Se publica en enero de 2027 | | | | | |

Los informes de enero de 2023 y 2024 traen valores redondeados a millones.

**Control 4. Lector del cuadro 1** (`tests/test_indec.py`, en la raíz del repositorio). La fila del acumulado del cuadro 1 se llama distinto según el mes del informe: "Total anual" en diciembre, "Total bimestre" en febrero (en el PDF, "Primer bimestre") y "Acumulado hasta..." el resto del año. La versión anterior del lector solo buscaba "Acumulado" y, si no la encontraba, tomaba la fila de enero. Por eso, en el informe de diciembre de 2025 leía un saldo de 162,1 (enero de 2025) en vez de 11.286. Esto no afectaba las cifras de la nota, que salen del informe de septiembre. Ahora:
- el lector detecta el mes del informe, toma la fila que corresponde y verifica que sea la suma de los meses de enero a ese mes;
- el test compara lo leído con el cuadro 1 del PDF de tres informes: diciembre de 2025 (20/01/2026, p. 7), febrero de 2026 (19/03/2026, p. 7) y septiembre de 2026 (19/10/2026, p. 7). También lo compara con los totales de los cuadros de rubros y usos del mismo Excel;
- el lector se probó en los 23 Excel de cuadros descargados (publicados entre el 19/01/2023 y el 19/10/2026). En todos detecta el mismo mes que el cuadro de rubros y usos y coincide con sus totales: la diferencia máxima es 0,275, en el informe del 20/08/2025, porque el cuadro 14 de ese informe trae las importaciones redondeadas a millones enteros (43.718,0 contra 43.717,8 en el cuadro 1; en 2024, 33.185,0 contra 33.184,7).

Para correrlo: `.venv/Scripts/python -m unittest discover -s tests -v`.

### Control: capítulo 27 de la NCM

**Nota metodológica.** El capítulo 27 de la Nomenclatura Común del Mercosur ("Combustibles minerales, aceites minerales y productos de su destilación; materias bituminosas; ceras minerales") es la apertura por producto que el INDEC publica en el cuadro 8 del informe técnico del ICA. No es la cifra de "balanza energética" que usan la Secretaría de Energía ni las consultoras, y no coincide con ninguna cifra publicada con ese nombre. Difiere de CyE − CyL porque son clasificaciones distintas: CyE es un gran rubro de exportación y CyL, un uso económico de importación. El saldo CyE − CyL supera al del capítulo 27 todos los años, entre 252,9 (2004) y 1.603,7 (2012), sobre todo por exportaciones. No se analizó qué productos explican la diferencia.

Archivo completo, 2004 a ene–sep 2026: `validacion/comparacion_cye_cyl_vs_cap27.csv`. Años seleccionados:

| Período | Saldo CyE − CyL | Saldo cap. 27 | Diferencia | Dif. expo (CyE − cap. 27) | Dif. impo (CyL − cap. 27) |
|---|---:|---:|---:|---:|---:|
| 2004 | 5.177,7 | 4.924,8 | 252,9 | 334,4 | 81,6 |
| 2013 | −6.902,5 | −8.459,0 | 1.556,5 | 2.003,6 | 447,1 |
| 2019 | −24,7 | −1.003,0 | 978,3 | 1.234,6 | 256,2 |
| 2022 | −4.386,4 | −5.875,8 | 1.489,3 | 1.544,3 | 54,9 |
| 2023 | 41,0 | −1.200,0 | 1.240,9 | 1.364,6 | 123,6 |
| 2024 | 5.730,0 | 4.461,4 | 1.268,6 | 1.477,9 | 209,2 |
| 2025 | 7.829,1 | 6.675,3 | 1.153,8 | 1.382,4 | 228,6 |
| Ene–sep 2025 | 5.359,1 | 4.503,2 | 855,9 | 1.031,3 | 175,4 |
| Ene–sep 2026 | 9.427,8 | 7.999,6 | 1.428,2 | 1.665,5 | 237,3 |

**Cómo se arma el capítulo 27 (solo para este control).** Anual: cuadros anuales por capítulo (`exp_ncm_AA_AA.xls`, `imp_ncm_AA_AA.xls`, del 2010–2014 al 2021–2025; para cada año, el cuadro más reciente). Para 2004–2009 no hay cuadro anual por capítulo y se usa la suma de los 12 meses de la API de Series de Tiempo (`162.3_XMB_MINION_0_0_56` y `163.3_MMBUSTIION_0_0_59`). Acumulados: cuadro 8 del informe del corte. Además, `datos/procesados/ica_cap27_mensual.csv` guarda una serie mensual desde 2004: la API hasta 12/2023 y, desde 01/2024, meses derivados de los acumulados oficiales de los 20 informes técnicos del 19/03/2025 al 19/10/2026. El método está en la docstring de `armar_cap27_mensual()` en `1_ica.py`.

**Resultados de los controles del capítulo 27** (todos en `validacion/`):
- `cap27_suma_meses_vs_oficial.csv`: la suma de los meses coincide con los acumulados del informe del corte (diferencia 0,0).
- `cap27_anual_vs_informes.csv`: el anual vigente difiere de la primera publicación en +47,0 (2024) y +12,3 (2025) por revisiones del INDEC.
- `cap27_api_vs_informes.csv`: en los 14 meses en que la API y los informes coinciden (01/2024–02/2025), las diferencias son de revisión: como máximo 20,4 en exportaciones y 11,8 en importaciones.
- `cap27_mes_publicado_vs_derivado.csv`: compara cada mes derivado con el mes tal como se publicó.
- `cap27_comex_vs_oficial.csv` (lo genera `control_comex.py`): desde 2018 el secreto estadístico tapa parte de las exportaciones del capítulo 27 en la base comex, entre el 4,4% y el 22,6% en los años de muestra (2018, 2020, 2022, 2024, 2025 y ene–sep 2026). En 2006 y 2015 la base coincide con el dato oficial. Por eso esa base no sirve como fuente.
- `control_unidades_cuadros_capitulos.csv`: todos los cuadros por capítulo están en millones de USD (cociente contra el total oficial entre 0,988 y 1,052).

### Lectura rápida de los resultados (para chequear que tengan sentido, no para publicar)

- **Saldo energético CyE − CyL:**
  - superávit entre 2004 y 2010, con un máximo de 6.080,8 en 2006;
  - déficit entre 2011 y 2019, con un mínimo de −6.902,5 en 2013;
  - superávit en 2020 (+952,9);
  - déficit en 2021 (−559,6) y en 2022 (−4.386,4);
  - casi equilibrio en 2023 (+41,0);
  - superávit de 5.730,0 en 2024 y de 7.829,1 en 2025.
- **Ene–sep 2026:** 9.427,8, contra 5.359,1 en ene–sep 2025 (+75,9%).
- **Últimos 12 meses a septiembre de 2026:** saldo energético de 11.897,7, el 44,9% del saldo comercial de bienes (26.472,2).
