# Informe de validación: producción de petróleo y gas

Series genéricas del bloque Energía (no atadas a una nota). Armador: `series/produccion_hidrocarburos.py`. Lectores: `scripts/secretaria_energia.py`. Última corrida: 25/11/2026 (Paso 1 del instructivo). Las secciones posteriores a "Actualización del 25/11/2026" describen la corrida del 18/11/2026 y quedan como antecedente; los CSV de `datos/validacion/` tienen los números vigentes.

## Actualización del 25/11/2026 (Paso 1): Vaca Muerta con la variante "DDJJ abiertas y cerradas"

Criterio aplicado (criterios, sección 3, aprobado el 19/11): volúmenes por pozo de la variante "DDJJ abiertas y cerradas" de cada año, y clasificación de cada pozo (tipo de recurso, subtipo y formación) tomada de la publicación más reciente de la SE que lo contiene. La base usa el dato vigente; la primera difusión queda como control.

**Versiones usadas** (todas consultadas el 25/11/2026; hashes en `versiones_crudos.csv`):
- Series agregadas de petróleo y gas: publicadas el 21/11/2026. Llegan a **10/2026**, que pasa a ser el último mes completo.
- DDJJ abiertas y cerradas 2010–2026: 17 archivos. Seis se republicaron después del 18/11; 2018, 2019, 2020, 2022 y 2024 con el mismo contenido (mismo hash; solo se anotó la fecha nueva) y 2026 con contenido nuevo (24/11/2026).
- Archivo no convencional: 22/11/2026 (contenido nuevo).
- Para la clasificación se usan los 17 DDJJ y el archivo no convencional en todas sus versiones guardadas (20 publicaciones: además, el DDJJ 2026 del 18/11 y el no convencional del 22/10).

**Controles** (`produccion_controles.csv`):
- **DDJJ con la clasificación vigente vs. serie agregada, 202 meses (01/2010–10/2026), `produccion_ddjj_vs_serie.csv`:** cierran todos, en total, shale y tight, petróleo y gas. Diferencia máxima: petróleo total 0,046 m³, gas total 0,019 miles de m³, shale y tight 0,0001.
- **Con la clasificación propia de cada archivo** no cierran 8 meses (gas shale de 05 a 12/2023, por ejemplo −12.241,91 miles de m³ en 08/2023): es el pozo reclasificado de 2023.
- **Clasificación:** ningún pozo tiene más de una clasificación dentro de una misma publicación; las 20 publicaciones tienen fechas distintas (no hay empates). Aplicar la regla por pozo o por pozo-mes da el mismo resultado (0 pozo-mes distintos).
- **Reclasificaciones (`produccion_reclasificaciones.csv`): 3 pozos.**
  - 164323 (Aguada Pichana Oeste, Neuquina): CONVENCIONAL / VMUT en el DDJJ 2023 (05/06/2026); NO CONVENCIONAL / SHALE / VMUT en el no convencional y en los DDJJ 2024–2026. 8 pozo-mes (05–12/2023), 0 m³ de petróleo y 71.544,42 miles de m³ de gas pasan de convencional a shale y a Vaca Muerta.
  - 164921 y 165823 (Cañadón Seco, Golfo San Jorge): siguen TIGHT; solo cambia la formación (CSEC y BBAR en el DDJJ 2023/2025 y en el no convencional del 22/10; POD1 en el del 22/11 y en el DDJJ 2026). No afectan shale, tight ni Vaca Muerta.
- **Vaca Muerta con los DDJJ vs. con el archivo no convencional (`produccion_vaca_muerta_ddjj_vs_no_convencional.csv`):** difieren solo los 4 meses en que el archivo no convencional no cerraba contra la serie: 06/2015 (+163,4 m³), 01/2019 (+501,7), 03/2019 (+18.024,2) y 09/2024 (+157.933,4 m³ de petróleo y +16.174,0 miles de m³ de gas). Septiembre de 2024 pasa de 385,3 a 418,45 kbbl/d.
- **Vaca Muerta en 07/2026:** 643,12 kbbl/d, contra 643,1 difundido (0,00%).

**Versiones de 2026.** La diferencia de +0,26% de 08 y 09/2026 (DDJJ del 18/11 contra serie del 21/10) desapareció: la serie del 21/11 sumó exactamente +11.906,0 m³ en agosto y +12.027,1 m³ en septiembre, y el DDJJ no cambió esos meses entre el 18/11 y el 24/11. Con las versiones vigentes, la diferencia de 08, 09 y 10/2026 es de −0,04 m³. Petróleo de septiembre de 2026: 972,15 kbbl/d (la serie del 21/10 daba 969,63; la primera difusión fue 973,7).

## Series generadas

| Archivo | Qué es | Período |
|---|---|---|
| `datos/procesados/produccion_petroleo_gas_mensual.csv` | Petróleo y gas, total y por subtipo de recurso (convencional, shale y tight): volumen del mes y promedio diario | 01/2006–10/2026 (al 25/11/2026) |
| `datos/procesados/produccion_vaca_muerta_mensual.csv` | Vaca Muerta (formprod VMUT + tipo de recurso NO CONVENCIONAL, con la clasificación más reciente de la SE; volúmenes de los DDJJ abiertas y cerradas): volumen del mes, promedio diario, pozos con registro y columna `control_shale_vs_serie` (hasta el 18/11 se llamaba `control_cobertura` y salía del archivo no convencional) | 01/2010–10/2026 (al 25/11/2026) |

**Unidades:**
- Petróleo: m³ del mes, m³/d (m³ ÷ días del mes) y kbbl/d (m³ × 6,28981 ÷ días del mes ÷ 1.000).
- Gas: miles de m³ del mes y MMm³/d (miles de m³ ÷ días del mes ÷ 1.000).

No hay tabla anual: el promedio anual es una decisión abierta hasta que una nota la necesite.

## Fuentes y versiones

Portal de la Secretaría de Energía (SE), datos.energia.gob.ar. Registro de versiones (fecha de publicación según el portal y SHA-256): `datos/validacion/versiones_crudos.csv`. Cada versión distinta se guarda en `datos/crudos/secretaria_energia/versiones/` sin pisar las anteriores.

| Archivo | Dataset / recurso | Publicado (portal) | Uso |
|---|---|---|---|
| Serie de petróleo por cuenca y sub tipo de recurso (Capítulo IV) | `c846e79c-026c-4040-897f-1ad3543b407c` / `af8c50bb-fde0-43b7-98eb-7cd14daf586c` | 21/10/2026 | Serie nacional |
| Serie de gas natural por cuenca y sub tipo de recurso (Capítulo IV) | ídem / `a3244ddd-38bc-4800-a700-360b649d2f3a` | 21/10/2026 | Serie nacional |
| Producción de pozos de gas y petróleo no convencional | ídem / `b5b58cdc-9e07-41f9-b392-fb9ec68b0725` | 22/10/2026 | Vaca Muerta |
| Producción de pozos de gas y petróleo 2026 (todos los pozos) | ídem / `fb7a47a0-cba9-4667-a004-6f6c1c346c23` | 18/11/2026 | Controles |
| Producción de pozos de gas y petróleo 2024 (todos los pozos) | ídem / `94d82d18-488b-434c-806d-ee5e053ce1cd` (el más reciente de los dos recursos de 2024) | 18/11/2026 | Controles |
| Producción de pozos de gas y petróleo 2024, recurso anterior (todos los pozos) | ídem / `43a09dce-1742-44d0-bc13-f193deaab563` | 03/10/2026 | Diagnóstico de 09/2024 (solo evidencia) |
| Producción de pozos de gas y petróleo 2024, DDJJ abiertas y cerradas (todos los pozos) | ídem / `0a352dee-8b4e-4e95-b01e-5b8082ce22ac` | 18/11/2026 | Diagnóstico de 09/2024 (solo evidencia) |
| Producción de pozos de gas y petróleo 2015 (todos los pozos) | ídem / `e375aa35-fd8d-41d6-aa0c-e6879ca567a1` | 12/11/2026 | Controles |
| SESCO, producción promedio diaria por cuenca, petróleo y gas | `590d1284-fd6d-4686-afd8-b3da5d90a6e9` / `570015c9-…` y `6a7866a1-…` | 21/12/2025 (petróleo) y 18/11/2026 (gas) | Controles |

**De la serie agregada hay una sola versión: la del 21/10/2026.** El 18/11/2026 la consulté de nuevo: el portal sigue informando el 21/10 y el hash es el mismo. Los datos más recientes de 2026 están en el archivo anual por pozo (18/11). La serie procesada usa la serie agregada del 21/10. Usar el archivo por pozo para 2026 sería mezclar fuentes: es una decisión abierta hasta que una nota la necesite.

## Controles internos de la serie agregada (`produccion_controles.csv`)

- Sin meses faltantes, duplicados, vacíos ni negativos (01/2006–09/2026, 249 meses).
- **Unidades.** El portal no publica diccionario de campos. Se deducen de las columnas diarias de la propia SE: `total_diario` = total ÷ días (petróleo en m³), `kbbl_diario` = m³/d × 6,28981 ÷ 1.000, y en gas `total_diario` = total ÷ días ÷ 1.000 (miles de m³; diario en MMm³/d). La diferencia máxima es de 0,0002.
- **Subtipos.** La participación no convencional publicada es (shale + tight) ÷ total (diferencia máxima 0,00005 puntos). En los 6 meses de 2026 en que la serie y el archivo anual coinciden, el convencional (total − shale − tight) es igual a:
  - en petróleo, los pozos de tipo CONVENCIONAL;
  - en gas, los pozos de tipo CONVENCIONAL más los "SIN RESERVORIO" (6.117,1 miles de m³ en esos 6 meses).
- **Total contra suma de las cinco cuencas.** Coincide en gas. En petróleo hay diferencias de hasta 0,0062%, en 43 meses entre 04/2008 y 11/2013.

## Archivo no convencional vs. serie agregada

### Regla de la SE: pozo no convencional sin subtipo = tight

En el archivo no convencional hay 460 filas sin subtipo (formprod PAIK, SPRI y VMUT), repartidas en 64 meses. Se probaron tres hipótesis contra la serie de la SE (`produccion_regla_sin_subtipo.csv`):

| Hipótesis | Meses en que cierra, petróleo | Meses en que cierra, gas |
|---|---:|---:|
| No se cuentan | 0 de 64 | 0 de 64 |
| Se cuentan como tight | **64 de 64** | **64 de 64** |
| Se cuentan como shale | 0 de 64 | 0 de 64 |

Ejemplo, julio de 2026: tight por pozo 22.799,1 m³ + sin subtipo 349,4 m³ = 23.148,5 m³; la serie publica 23.148,6 m³.

### Meses que no cierran (`produccion_meses_que_no_cierran.csv`)

Con la regla aplicada, shale y tight coinciden con la serie en todos los meses menos estos. La diferencia es archivo no convencional menos serie:

| Mes | Producto | Subtipo | Diferencia | Por día | % de la serie |
|---|---|---|---:|---:|---:|
| 01/2007 | Petróleo | Tight | −9,4 m³ | −0,002 kbbl/d | −1,03% |
| 01/2007 | Gas | Tight | −690,4 miles de m³ | −0,022 MMm³/d | −2,00% |
| 06/2015 | Petróleo | Shale | −163,4 m³ | −0,034 kbbl/d | −0,16% |
| 06/2015 | Petróleo | Tight | −135,4 m³ | −0,028 kbbl/d | −0,84% |
| 06/2015 | Gas | Shale | −1.344,4 miles de m³ | −0,045 MMm³/d | −1,44% |
| 06/2015 | Gas | Tight | −2.755,6 miles de m³ | −0,092 MMm³/d | −0,55% |
| 01/2019 | Petróleo | Shale | −501,7 m³ | −0,102 kbbl/d | −0,13% |
| 01/2019 | Petróleo | Tight | −2.128,9 m³ | −0,432 kbbl/d | −5,33% |
| 01/2019 | Gas | Shale | −220,9 miles de m³ | −0,007 MMm³/d | −0,03% |
| 01/2019 | Gas | Tight | −41.243,4 miles de m³ | −1,330 MMm³/d | −5,49% |
| 03/2019 | Petróleo | Shale | −18.024,2 m³ | −3,657 kbbl/d | −4,79% |
| 03/2019 | Gas | Shale | −2.957,7 miles de m³ | −0,095 MMm³/d | −0,33% |
| **09/2024** | **Petróleo** | **Shale** | **−157.933,4 m³** | **−33,112 kbbl/d** | **−7,91%** |
| 09/2024 | Gas | Shale | −16.174,0 miles de m³ | −0,539 MMm³/d | −0,69% |

En todos los casos el archivo no convencional suma menos que la serie. En 09/2024 el archivo tiene 2.410 pozos shale, contra 2.528 en 08/2024 y 2.589 en 10/2024.

## Cobertura del archivo no convencional vs. archivos anuales completos (`produccion_cobertura_no_convencional.csv`)

| Año contrastado | Pozo-mes NO CONVENCIONAL en los dos | Solo en el anual | Solo en el no convencional | Con volumen distinto |
|---|---:|---:|---:|---:|
| 2015 | 12.841 | 0 | 0 | 0 |
| 2024 | 48.451 | 0 | 0 | 0 |
| 2026, solo enero–septiembre | 44.630 | 0 | 0 | 0 |

**El archivo no convencional reproduce exactamente a los tres anuales completos.**

La cobertura de 2026 se contrastó solo de enero a septiembre, el último mes completo de la fuente oficial. El anual de 2026 (18/11) trae también octubre de 2026, pero parcial: 20.523 pozo-mes, 385 de ellos NO CONVENCIONAL (que no están en el archivo no convencional, que termina en septiembre), y 133,8 kbbl/d en total. Octubre no entra en el contraste ni en ninguna serie (ver "Corte").

## Archivos anuales completos vs. serie agregada (`produccion_anuales_vs_serie.csv`)

Todos los pozos del archivo anual contra la serie agregada, por mes: total, shale y tight (con la regla de tight). Diferencias de anual menos serie, sin contar las de redondeo (0,5 o menos):

| Año | Mes | Petróleo total | Petróleo shale | Petróleo tight | Gas total | Gas shale |
|---|---|---:|---:|---:|---:|---:|
| 2015 | 06 | −103.042,5 m³ | −163,4 | −135,4 | −112.934,1 miles de m³ | −1.344,4 |
| 2024 | 09 | −157.933,4 m³ | −157.933,4 | 0 | −16.174,1 miles de m³ | −16.174,0 |
| 2026 | 06 | −5.016,6 m³ | 0 | 0 | −18.668,7 miles de m³ | 0 |
| 2026 | 08 | +11.906,0 m³ | 0 | 0 | +2.087,9 miles de m³ | 0 |
| 2026 | 09 | +12.027,1 m³ | 0 | 0 | +1.827,8 miles de m³ | 0 |

Los otros meses de los tres años coinciden.
- **2015 y 2024 son faltantes en los datos por pozo.** El anual completo de cada año queda debajo de la serie agregada.
- **2026 son revisiones entre versiones.** La serie es del 21/10 y el anual, del 18/11 (ver "Versiones de 2026").

### Diagnóstico de septiembre de 2024

- **El anual oficial completo de 2024 (18/11/2026) tiene el mismo hueco** que el archivo no convencional: −157.933,4 m³ de petróleo (todo shale) y −16.174,1 miles de m³ de gas contra la serie agregada. Los dos archivos por pozo coinciden exactamente entre sí.
- **Qué falta:** 111 pozos shale de la formación VMUT, todos de una misma operadora, tienen producción de petróleo en agosto y octubre de 2024 y ningún registro en septiembre. En agosto produjeron 160.450 m³ (32,6 kbbl/d) y en octubre 141.803 m³ (28,8 kbbl/d): el mismo orden que el faltante. Los registros shale por mes son 2.528 en agosto, 2.410 en septiembre y 2.589 en octubre.
- **La serie agregada de la SE sí incluye ese volumen.** No se encontró un dato oficial por pozo con el que completar el mes.
- **No se completó ni se estimó nada.** La serie de Vaca Muerta lo marca en `control_cobertura`, como a 06/2015, 01/2019 y 03/2019. En septiembre de 2024 da 385,3 kbbl/d, contra 402,3 en agosto y 421,4 en octubre.
- **Las otras dos versiones de 2024 en el portal** (bajadas el 18/11/2026 solo como evidencia; no se usan en ninguna serie):
  - **Recurso anterior** (`43a09dce-1742-44d0-bc13-f193deaab563`, publicado el 03/10/2026, sha256 `2c3e2f6ec268…`). Es igual al del 18/11 en todos los meses: el mismo faltante en 09/2024.
  - **Variante "DDJJ abiertas y cerradas"** (`0a352dee-8b4e-4e95-b01e-5b8082ce22ac`, publicada el 18/11/2026, sha256 `5216342c5c3a…`, 307,6 MB). **Trae septiembre de 2024 de los 111 pozos que faltan.**
- **Qué agrega esa variante:**
  - 159 filas que no están en el recurso del 18/11. Todas son de 09/2024 y de una sola operadora (código `SHE` de la SE):
    - 150 son NO CONVENCIONAL shale y suman 157.933,4 m³ de petróleo y 16.174,0 miles de m³ de gas: exactamente el faltante.
    - Las otras 9 (5 CONVENCIONAL y 4 SIN RESERVORIO) no tienen producción.
    - De esos 150, los 111 pozos con producción en agosto y octubre aportan 150.992,5 m³. Su fecha de carga es el 17/10/2024.
  - En las demás filas, las dos versiones son iguales.
  - **Con esa variante, el total de petróleo de cada uno de los 12 meses de 2024 coincide con la serie agregada** (diferencia 0,0 m³).
- **Lectura (inferida, no documentada por la SE):** la serie agregada se arma con las declaraciones juradas abiertas y cerradas, y los otros archivos por pozo (el anual "normal" y el no convencional) traen solo las cerradas. La declaración de septiembre de 2024 de esa operadora estaría abierta.
- **No se completó nada.** Cambiar la fuente de los datos por pozo a la variante "DDJJ abiertas y cerradas" es una decisión pendiente de Agustín. Los otros meses que no cierran (01/2007, 06/2015, 01/2019 y 03/2019) no se contrastaron con esa variante.

## Corte

Ninguna serie puede tener meses posteriores al último mes completo de la fuente oficial: el último mes de la serie agregada de la SE (hoy, 09/2026). Los archivos por pozo traen meses parciales (10/2026 en el anual de 2026). La función `verificar_corte()` detiene el script si una serie se pasa; además hay un control en `produccion_controles.csv`. En `produccion_versiones_2026.csv`, octubre de 2026 aparece solo como evidencia, marcado con `mes_completo_en_fuente_oficial = False`.

## Versiones de 2026: serie agregada (21/10) vs. archivo anual por pozo (18/11) (`produccion_versiones_2026.csv`)

| Mes | Petróleo, anual − serie (m³) | Gas, anual − serie (miles de m³) | Filas cargadas después del 21/10 | Petróleo de esas filas (m³) |
|---|---:|---:|---:|---:|
| 01–05/2026 y 07/2026 | 0,0 | 0,0 | 0 | 0,0 |
| 06/2026 | −5.016,6 | −18.668,7 | 0 | 0,0 |
| 08/2026 | +11.906,0 | +2.087,9 | 21 | 0,0 |
| 09/2026 | +12.027,1 | +1.827,8 | 3.033 | **12.027,1** |
| 10/2026 | (no está en la serie) | | 20.523 | 659.455,9 (mes parcial) |

- **Septiembre de 2026 estaba incompleto en la serie del 21/10.** Los 3.033 registros cargados entre el 22/10 y el 30/10 (según `fechaingreso`) suman exactamente la diferencia. Con el archivo del 18/11, septiembre da 972,15 kbbl/d, contra 969,63 en la serie.
- **Junio y agosto cambian sin registros nuevos.** No hay filas de esos meses cargadas después del 21/10 con producción. La fecha de carga no explica esas revisiones; el mecanismo no está verificado.
- **Las revisiones van en los dos sentidos.** Junio de 2026 bajó: 914,19 kbbl/d en la serie del 21/10 contra 913,14 en el anual del 18/11 (−1,05 kbbl/d; gas −0,62 MMm³/d). Agosto y septiembre subieron (+2,42 y +2,52 kbbl/d). Contra la primera difusión pasa lo mismo: diciembre de 2025 subió 1,18% y septiembre de 2026 quedó debajo.
- **Octubre de 2026 es un mes parcial** en el archivo anual (unos 134 kbbl/d): los meses recientes se completan de a poco.

## Primera difusión vs. dato vigente (`produccion_vs_primera_difusion.csv`)

Sin tolerancia de aprobado o rechazado: se muestra la revisión. La revisión es dato menos primera difusión, en %.

| Serie | Mes | Primera difusión | Fuente (ver abajo) | Serie agregada (21/10) | Revisión | Por pozo (18/11) | Revisión | SESCO | Revisión |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|
| Petróleo | 10/2025 | 859,5 kbbl/d | A | 860,38 | +0,10% | — | | 850,85 | −1,01% |
| Petróleo | 12/2025 | 868,7 kbbl/d | B | 878,94 | +1,18% | — | | — | |
| Petróleo | 05/2026 | 903,7 kbbl/d | C | 903,98 | +0,03% | 903,98 | +0,03% | — | |
| Gas | 05/2026 | 156,6 MMm³/d | C (1) | 156,63 | +0,02% | 156,63 | +0,02% | 156,47 | −0,08% |
| Petróleo | 07/2026 | 916,2 kbbl/d | D | 918,08 | +0,20% | 918,08 | +0,20% | — | |
| Gas | 07/2026 | 158,8 MMm³/d | D | 158,13 | −0,42% | 158,13 | −0,42% | 158,43 | −0,23% |
| Vaca Muerta, petróleo | 07/2026 | 643,1 kbbl/d | D | 643,12 (archivo no convencional) | +0,00% | | | | |
| Petróleo | 09/2026 | 973,7 kbbl/d | E | 969,63 | −0,42% | 972,15 | −0,16% | — | |
| Gas | 09/2026 | 143,1 MMm³/d | F | 142,31 | −0,56% | 142,37 | −0,51% | 142,87 | −0,16% |

1. La agregué yo: aparece en la misma fuente que el petróleo de mayo.

SESCO petróleo termina en 11/2025 (publicado el 21/12/2025).

**Fuentes de primera difusión.** Las busqué el 18/11/2026 y verifiqué el texto en copias de cada página. En ninguna se dice de qué base sale el dato (Capítulo IV, SESCO, preliminar) ni se define el gas: dicen "gas natural" o "el gas".
- **A. Petróleo 10/2025.** Post en X de la Secretaría de Energía (@Energia_Ar), 20/11/2025: https://x.com/Energia_Ar/status/1991579025807143398. Dice "859.5 Mbbl promedio por día". No pude abrir x.com (HTTP 402): lo leí embebido en https://www.memo.com.ar/economia/record-argentina-octubre-2025-petroleo-produccion/. No hay comunicado en argentina.gob.ar.
- **B. Petróleo 12/2025.** Post en X del Ministerio de Economía (@MinEconomia_Ar), 22/01/2026: https://x.com/MinEconomia_Ar/status/2014291960077725735. Dice "868.712 barriles por día". Lo leí embebido en https://www.lacapitalmdp.com/argentina-alcanzo-un-record-en-la-produccion-de-petroleo/. No hay comunicado en argentina.gob.ar. El diario Río Negro publicó la cifra el 21/01/2026, un día antes, "procesada" del registro de la SE.
- **C. Petróleo y gas 05/2026.** Transcripción oficial de la conferencia de prensa del vocero presidencial del 30/06/2026: https://www.casarosada.gob.ar/informacion/conferencias/51305-conferencia-de-prensa-del-vocero-presidencial-adrian-ravier-desde-casa-rosada-30-06-2026. Dice "903.700 barriles diarios" y "el gas alcanzó los 156.6 millones de metros cúbicos diarios". No hay comunicado en argentina.gob.ar.
- **D. Petróleo, gas y Vaca Muerta 07/2026.** Comunicado oficial del Ministerio de Economía (Energía) del 24/08/2026: https://www.argentina.gob.ar/noticias/la-produccion-de-petroleo-registro-otro-mes-de-crecimiento-en-julio. Dice "916,2 mil barriles diarios", "643,1 mil barriles diarios" (Vaca Muerta) y "158,8 millones de metros cúbicos diarios".
- **E. Petróleo 09/2026.** No encontré comunicado oficial de primera difusión. La prensa del 21/10/2026 (DolarHoy) atribuye la cifra a la Secretaría de Energía. Hay una mención oficial posterior, del Ministerio de Economía el 11/11/2026: https://www.argentina.gob.ar/noticias/ya-esta-abierta-la-inscripcion-para-la-segunda-ronda-de-negocios-rigi-con-foco-en ("973.700 barriles diarios").
- **F. Gas 09/2026.** No encontré fuente oficial. Solo prensa: DolarHoy (21/10/2026, sin atribución) e iProfesional (informe de RICSA con datos de la SE).

Qué revisé: noticias de la Secretaría de Energía (argentina.gob.ar/node/11603/noticias, de nov-2026 a jun-2024) y del Ministerio de Economía (argentina.gob.ar/node/50691/noticias); el buscador de argentina.gob.ar con cada cifra y con términos generales; las 36 conferencias de prensa de casarosada.gob.ar entre el 30/10/2025 y el 17/11/2026; y prensa para rastrear cada anuncio. En x.com no pude leer los posts directamente.

### Gas: la diferencia no está explicada

Lo verificado:
- **No es una diferencia sistemática.** En mayo de 2026 la cifra oficial (156,6) coincide con el Capítulo IV (156,63, +0,02%). En julio el Capítulo IV da 0,42% menos que el comunicado oficial. En septiembre da 0,56% menos, pero esa cifra no tiene fuente oficial.
- **No son datos cargados tarde.** Julio de 2026 es idéntico en la serie (21/10) y en el archivo por pozo (18/11). En septiembre, lo cargado después del 21/10 agrega 0,06 MMm³/d.
- **Ninguna serie de la SE reproduce lo difundido.** La serie SESCO de gas (SE, publicada el 18/11/2026) da 158,43 y 142,87: más cerca de lo difundido que el Capítulo IV, pero tampoco lo reproduce (−0,23% y −0,16%).
- **El Capítulo IV y SESCO también difieren entre sí en 2026**, entre −0,40% y +0,11% según el mes. Hasta 2021, y en 2024 y 2025, coinciden.

Lo no verificado:
- si la cifra difundida usa otra definición de gas (por ejemplo, con o sin gas inyectado o venteado) u otra fuente preliminar: ningún texto oficial lo dice;
- si julio se revisó a la baja entre el comunicado (24/08) y el 21/10: no tengo la versión de los datos de agosto.

No se ajustó nada para que cierre.

## Decisiones abiertas hasta que una nota las necesite

*Actualizado el 25/11/2026:* los puntos 2 a 4 quedaron resueltos (criterios, sección 3, y arquitectura aprobada): la base guarda hasta el último mes completo de cada fuente y el corte lo define cada nota; la serie es el dato vigente de la SE; Vaca Muerta sale de la variante "DDJJ abiertas y cerradas", que cubre los meses que faltaban (09/2024 y los demás). Sigue abierto el 1.

1. Promedio anual (volumen ÷ días o promedio de meses) y presentación del año en curso.
2. *(Resuelto)* Corte común o último dato disponible por serie.
3. *(Resuelto)* Fuente de los meses recientes.
4. *(Resuelto)* Qué hacer con los meses que los datos por pozo no cubren.

La base guarda las dos fuentes y todas sus versiones:
- las series procesadas salen de la serie agregada (nacional) y de los DDJJ abiertas y cerradas con la clasificación más reciente (Vaca Muerta);
- los archivos por pozo y cada versión de cada crudo quedan en `datos/crudos/secretaria_energia/versiones/` (registro en `versiones_crudos.csv`);
- la comparación mes a mes entre las dos fuentes queda en `produccion_versiones_2026.csv` y `produccion_anuales_vs_serie.csv`.
