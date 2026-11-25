# La vuelta del gas

> **En pausa desde el 25/11/2026.** La nota 1 de El Pozo y el Péndulo cambió de pregunta y de foco (ver `nota-1-estructura.md` en la carpeta de trabajo): esta carpeta queda como registro y no se borra ni se renombra. La nota nueva tiene su propia carpeta.
>
> **Desde el Paso 3b de la migración** esta nota ya no arma series: `1_ica.py` lee solo la base (`datos/series/`) y arma g1, g2 y las cifras para el texto con su corte (septiembre de 2026). Son idénticos, byte a byte, a los commiteados antes de la migración (`b0909cd`); lo controla `tests/test_migracion_ica.py`.
>
> **Base con que se armaron:** ver "Nota congelada", al final.

Datos y código de la nota de **El Pozo y el Péndulo** de diciembre de 2026, en [Sobre Modelos y Tumbas](https://sobremodelosytumbas.substack.com).

**Pregunta:** ¿cuánto del saldo comercial de bienes de la Argentina explica hoy la energía, y cuánto de eso es estructural (más producción, Vaca Muerta) y cuánto coyuntural (precios internacionales)?

**Definición del saldo energético:** exportaciones de **Combustibles y energía (CyE)** menos importaciones de **Combustibles y lubricantes (CyL)**, del Intercambio comercial argentino (ICA) del INDEC. Es la cifra que usan la Secretaría de Energía y las consultoras. El capítulo 27 de la Nomenclatura Común del Mercosur queda solo como control.

**Período:** desde 2004, el comienzo de la serie mensual oficial. **Corte:** septiembre de 2026 (informe del ICA del 19/10/2026).

## Cómo reproducir todo

Desde la raíz del repositorio, con Python 3.12:

```
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt      # en Linux/Mac: .venv/bin/python
.venv/Scripts/python actualizar.py --bloque energia --crudos-al 2026-11-18   # la base, con los crudos del 18/11/2026
.venv/Scripts/python notas/2026-12-la-vuelta-del-gas/correr_todo.py
```

`--crudos-al` arma la base con las versiones de los crudos que había el 18/11/2026 (necesita esas versiones guardadas en `datos/crudos/*/versiones/`). Sin esa opción, la base se actualiza con lo último que publicó el INDEC y g2 puede cambiar por revisiones: la nota está congelada a la base del commit indicado abajo. El mes de corte está fijo en `1_ica.py` (`MES_DE_CORTE`).

## Archivos

| Archivo | Qué es |
|---|---|
| `correr_todo.py` | Corre todo en orden. |
| `1_ica.py` | Lee la base y arma g1, g2, las cifras para el texto y el control propio de la nota. |
| `control_comex.py` | Muestra el control del capítulo 27 en la base comex, que desde el Paso 3b corre la base (`datos/validacion/sector_externo/cap27_comex_vs_oficial.csv`). |
| `cifras_para_el_texto.csv` | **Las cifras que se citan en la nota**: CyE, CyL, saldo energético y su peso en el saldo comercial de bienes en 2023, 2024, 2025, ene–sep 2025, ene–sep 2026 y últimos 12 meses. Salen solo de anuales y acumulados oficiales. |
| `informe_validacion.md` | Histórico al 18/11/2026: fuentes, definiciones y contrastes. El vigente es `datos/validacion/sector_externo/informe_validacion.md`. |
| `graficos/g1_balanza_energetica_anual.csv` | Exportaciones de CyE, importaciones de CyL y saldo por año (2004–2025, anuales oficiales), más ene–sep del año anterior y del año en curso (acumulados oficiales del informe del corte). |
| `graficos/g2_saldo_energetico_vs_total_12m.csv` | Saldo energético (CyE − CyL) y saldo comercial de bienes, suma de 12 meses, mensual desde diciembre de 2004. |
| `graficos/*.png` | Gráficos rápidos para revisar los CSV (no son los de la nota). |
| `validacion/controles_nota.csv` | Control propio de la nota (los 12 meses derivados de cifras oficiales = el último punto de g2). |
| `validacion/` (el resto) | **Copia congelada al 18/11/2026.** Los controles vigentes del comercio exterior y del saldo energético están en `datos/validacion/sector_externo/` y `datos/validacion/energia/`. |

La nota ya no genera series. Las que usa están en la base:

| Archivo | Qué es |
|---|---|
| `datos/series/sector_externo/ica_mensual.csv` | Mensual desde 2004: exportaciones e importaciones totales, CyE, CyL y saldo comercial de bienes. |
| `datos/series/sector_externo/ica_anual.csv` | Anual oficial: totales, CyE, CyL y capítulo 27, con la marca de dato provisorio. |
| `datos/series/sector_externo/ica_acumulados_informes.csv` | Acumulados oficiales que publica cada informe (de ahí salen los de ene–sep). |
| `datos/series/energia/balanza_energetica_mensual.csv` y `_anual.csv` | Saldo energético CyE − CyL. |

## Formato de los CSV de gráficos

Punto decimal, coma como separador de columnas y una fila por período, listos para pegar en Datawrapper (que después los muestra con formato argentino). Valores en millones de dólares corrientes; exportaciones FOB, importaciones CIF.

Fuente sugerida para los gráficos: *"Fuente: INDEC, Intercambio comercial argentino. Exportaciones de Combustibles y energía (CyE) menos importaciones de Combustibles y lubricantes (CyL). 2024 y 2025, datos provisorios; 2026, exportaciones estimadas e importaciones provisorias."* (son las marcas del INDEC en los cuadros del informe del 19/10/2026). La serie no tiene valores estimados por nosotros, así que no lleva nota de estimación.

## Estado

- [x] Etapa 1: saldo energético y saldo comercial de bienes (g1, g2)
- [ ] Etapa 2: producción de petróleo y gas (g3) — no se hará: la nota está en pausa
- [ ] Etapa 3: precios y cantidades (g4) — ídem

## Nota congelada

g1, g2 y las cifras se armaron con la base del commit que se anota abajo (crudos al 18/11/2026). Para reproducirlos exactamente: `git checkout <commit>`, y después los dos comandos de "Cómo reproducir todo".

- Commit de la base: *(se anota en el commit siguiente al del Paso 3b)*
