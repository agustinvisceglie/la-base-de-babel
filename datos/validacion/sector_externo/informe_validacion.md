# Informe de validación: comercio exterior (ICA) y balanza energética

Bloques: sector externo (`bloques/sector_externo/comercio_exterior.py`) y energía (`bloques/energia/balanza_energetica.py`). Lectores: `lectores/indec.py`, `lectores/api_series_tiempo.py` y `lectores/indec_comex.py`. Migrado desde la nota "La vuelta del gas" en el Paso 3b (25/11/2026). Los números de este informe son los de la corrida de esa fecha, armada con los crudos del 18/11/2026 (`actualizar.py --crudos-al 2026-11-18`); los CSV de esta carpeta tienen siempre los de la última corrida.

## Series

| Archivo (`datos/series/`) | Qué es | Período |
|---|---|---|
| `sector_externo/ica_mensual.csv` | Exportaciones e importaciones totales, Combustibles y energía (CyE), Combustibles y lubricantes (CyL) y saldo comercial de bienes | 01/2004 al mes del último informe |
| `sector_externo/ica_anual.csv` | Anual oficial de lo mismo, más el capítulo 27 de la NCM (control), la marca `provisorio` y los cuadros de origen | 1980 al último año publicado |
| `sector_externo/ica_cap27_mensual.csv` | Capítulo 27 mensual (control), con la fuente de cada mes | 01/2004 al mes del último informe |
| `sector_externo/ica_acumulados_informes.csv` | Acumulados oficiales del año que publica cada informe usado (cuadro 1, rubros y usos, capítulo 27), del año en curso y del anterior | Informes desde 03/2025 y los de enero desde 2023 |
| `energia/balanza_energetica_mensual.csv` y `_anual.csv` | Saldo energético = CyE − CyL (criterios, sección 1) | Ídem |

- Unidad: millones de USD corrientes; exportaciones FOB e importaciones CIF. Los CSV guardan 8 decimales: la fuente trae centavos de USD.
- La base guarda hasta el último mes de la fuente (el del informe más reciente); cada nota pone su corte.
- No hay valores estimados.

## Fuentes (todas del INDEC)

| Qué | Dónde |
|---|---|
| Listado de informes técnicos del ICA | https://www.indec.gob.ar/Institucional/Indec/InformesTecnicos/40 |
| Excel de cuadros de cada informe | https://www.indec.gob.ar/ftp/cuadros/economia/ica_cuadros_DD_MM_AA.xls |
| Serie mensual por rubros y usos (versión interactiva del informe más reciente) | https://www.indec.gob.ar/ftp/ica_digital/ica_d_MM_AA&lt;código&gt;/data/cuadros/serie_rubros_usos_mensual.xlsx |
| Cuadros anuales por rubro y uso, y por capítulo | Página del ICA, https://www.indec.gob.ar/Nivel4/Tema/3/2/40 (exp_gr_80_AA.xls, imp_uso_econ_80_AA.xls, exp_ncm_AA_AA.xls, imp_ncm_AA_AA.xls) |
| Capítulo 27 mensual hasta 02/2025 (control) | API de Series de Tiempo, IDs 162.3_XMB_MINION_0_0_56 y 163.3_MMBUSTIION_0_0_59 |
| Base por posición NCM (control del capítulo 27) | https://comex.indec.gob.ar/files/zips/exports_AAAA_M.zip e imports_AAAA_M.zip |

Cada crudo se guarda como versión comprimida con su hash en `datos/registros/versiones_crudos.csv`. Los crudos del 18/11/2026 se registraron como versiones con `comun/registrar_crudos_previos.py`, después de verificar que su SHA-256 es el que anotó la nota al bajarlos.

## Controles (`comercio_exterior_controles.csv` y `energia/balanza_energetica_controles.csv`)

Todos OK en la corrida del 25/11/2026:
- series sin meses faltantes, de 01/2004 al mes del último informe (09/2026);
- 0 ≤ CyE ≤ exportaciones totales y 0 ≤ CyL ≤ importaciones totales;
- la serie mensual suma los anuales oficiales 2004–2025 (diferencia máxima 0,0016 millones de USD) y los acumulados del último informe (diferencia 0);
- lo leído de los Excel de cuadros coincide con lo publicado en el PDF (17 de 17 valores, `control_valores_publicados.csv`);
- unidades de los cuadros por capítulo: total del cuadro / total oficial entre 0,9884 y 1,0522 (`control_unidades_cuadros_capitulos.csv`);
- capítulo 27: saldo = exportaciones − importaciones en los cuadros, y la suma de los meses da los acumulados del último informe (diferencia 0);
- el saldo CyE − CyL publicado por terceros coincide con la primera publicación del INDEC: 2022 = −4.470 (IAE Mosconi y Más Energía), 2024 = 5.668 (Secretaría de Energía), 2025 = 7.815 (IARAF), ene–ago 2026 = 7.834 (Economía & Energía y RICSA).

## Primera publicación vs. dato vigente (`energia/cye_cyl_anual_vs_informes.csv` y `cye_cyl_vs_referencias_publicadas.csv`)

La base usa el dato vigente (criterios, sección 1). El INDEC revisa los años en los dos sentidos: 2022 se publicó en −4.470 y hoy es −4.386,4; 2023 se publicó en −46 y hoy es +41,0; 2024 se publicó en 5.667,8 y hoy es 5.730,0; 2025 se publicó en 7.815,1 y hoy es 7.829,1.

## Capítulo 27 (control)

- `energia/comparacion_cye_cyl_vs_cap27.csv`: CyE − CyL contra el capítulo 27, anual y acumulado.
- `cap27_suma_meses_vs_oficial.csv`, `cap27_api_vs_informes.csv`, `cap27_mes_publicado_vs_derivado.csv` y `cap27_anual_vs_informes.csv`: cómo se derivan los meses y cuánto revisa el INDEC.
- `cap27_comex_vs_oficial.csv`: en la base por posición NCM, desde 2018 el secreto estadístico tapa parte de las exportaciones del capítulo 27 (−22,6% en 2018; −4,4% en ene–sep 2026). Por eso esa base no es la fuente.

## Migración (Paso 3b): qué cambió respecto de lo commiteado en `b0909cd`

Con los crudos del 18/11/2026, todos los números de `ica_mensual`, `ica_anual` e `ica_cap27_mensual` son iguales a los commiteados (a 3 decimales, como se publicaron), y g1, g2 y las cifras de la nota son idénticos byte a byte (`tests/test_migracion_ica.py`). Cambios de forma:
- el saldo CyE − CyL pasó de `ica_mensual` e `ica_anual` a `energia/balanza_energetica_*.csv`;
- los CSV guardan 8 decimales en lugar de 3 (con 6 decimales, tres celdas que valían, por ejemplo, 5001,6074999 se redondeaban dos veces y daban distinto en el tercer decimal);
- `ica_anual` suma dos columnas auxiliares con el nombre de los cuadros anuales;
- en `cap27_comex_vs_oficial.csv`, el acumulado oficial de 2026 ya no se toma redondeado a un decimal de otra tabla: la diferencia de exportaciones de ene–sep 2026 da −472,5 (antes −472,6) y algunas diferencias nulas pasan de "−0,0" a "0,0";
- dos textos que nombraban la nota ("informe del corte") ahora dicen "último informe" o "serie mensual vigente".
