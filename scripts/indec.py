"""
INDEC: descarga y lectura de los cuadros en Excel del sitio www.indec.gob.ar.

Qué hace:
    - buscar_archivos(): lee una página temática del INDEC y encuentra la URL vigente de cada
      cuadro según el comienzo de su nombre (el INDEC cambia los nombres cada año, por ejemplo
      expo_grandes_rubros_2025_2026.xls pasa a ser expo_grandes_rubros_2026_2027.xls).
    - leer_ica_mensual(): lee los cuadros mensuales del Intercambio comercial argentino (ICA)
      por grandes rubros (exportaciones) o por usos económicos (importaciones). Cada archivo
      trae dos años: el corriente y el anterior.
    - leer_ica_anual(): lee los cuadros anuales históricos por rubro o uso (desde 1980),
      que vienen en miles de USD, y los pasa a millones de USD.
    - listar_informes_ica(): lee el listado oficial de informes técnicos del ICA y devuelve,
      para cada uno, la fecha de publicación y las URL del PDF, del Excel de cuadros y de la
      versión interactiva.
    - leer_cuadro_capitulo27(): lee, del Excel de cuadros de un informe, la balanza comercial
      del capítulo 27 de la NCM (combustibles minerales): mes del informe, mismo mes del año
      anterior y, si está, el acumulado del año.
    - leer_cuadro1_acumulado(): lee del cuadro 1 el acumulado del año de exportaciones,
      importaciones y saldo comercial de bienes, en informes de cualquier mes (la fila del
      acumulado se llama distinto en enero, febrero y diciembre; ver tests/test_indec.py).
    - leer_cuadro_rubros_usos(): lee, del Excel de cuadros de un informe, las exportaciones de
      Combustibles y energía (CyE) y las importaciones de Combustibles y lubricantes (CyL), del
      mes y acumuladas, para el año en curso y el anterior.
    - leer_capitulo_anual(): lee un cuadro anual por capítulos de la NCM (exp_ncm_AA_AA.xls,
      imp_ncm_AA_AA.xls) y devuelve la fila del capítulo 27.
    - leer_rubros_usos_mensual(): lee la serie mensual por grandes rubros y usos económicos de
      la versión interactiva del informe (serie_rubros_usos_mensual.xlsx, desde 2004).

Fuente: INDEC, página "Intercambio comercial argentino" (https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-2-40),
    listado de informes técnicos del ICA y versión interactiva de cada informe.
Genera: los archivos originales en datos/crudos/indec/ (no se modifican).
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import xlrd

from scripts.descargas import CRUDOS, RAIZ, descargar

URL_INDEC = "https://www.indec.gob.ar"
# La página visible (Nivel4-Tema-3-2-40) carga su contenido desde esta dirección:
PAGINA_ICA = URL_INDEC + "/Nivel4/Tema/3/2/40"
CARPETA = CRUDOS / "indec"

MESES_ABREV = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def buscar_archivos(pagina: str, prefijos: list[str], nombre_html: str) -> tuple[dict[str, str], list[dict]]:
    """Devuelve {prefijo: url_completa} con el archivo vigente para cada prefijo.

    Si un prefijo aparece en más de un archivo, falla: preferimos que lo revise una persona.
    """
    registro = descargar(pagina, CARPETA / nombre_html)
    html = (RAIZ / registro["archivo"]).read_text(encoding="utf-8", errors="replace")
    enlaces = re.findall(r'href="([^"]+\.xlsx?)"', html, flags=re.IGNORECASE)

    encontrados = {}
    for prefijo in prefijos:
        candidatos = sorted({e for e in enlaces if Path(e).name.startswith(prefijo)})
        if len(candidatos) != 1:
            raise ValueError(f"Para '{prefijo}' se esperaba 1 archivo y hay {len(candidatos)}: {candidatos}")
        ruta = candidatos[0].replace("../../", "/")  # algunos enlaces son relativos
        encontrados[prefijo] = URL_INDEC + ruta if ruta.startswith("/") else ruta
    return encontrados, [registro]


def descargar_archivo(url: str) -> tuple[Path, dict]:
    """Baja un cuadro del INDEC a datos/crudos/indec/ con su nombre original."""
    destino = CARPETA / Path(url).name
    registro = descargar(url, destino)
    return destino, registro


def _texto(valor) -> str:
    return str(valor).strip()


def leer_ica_mensual(ruta: Path, etiqueta_rubro: str) -> pd.DataFrame:
    """Lee expo_grandes_rubros_AAAA_AAAA.xls o impo_uso_economico_AAAA_AAAA.xls.

    `etiqueta_rubro` es el comienzo del encabezado de la columna buscada,
    por ejemplo "Combustibles y energía" o "Combustibles y lubricantes".
    Devuelve una tabla mensual (índice = primer día del mes) con las columnas
    `total` y `rubro`, en millones de USD.
    """
    hoja = xlrd.open_workbook(ruta).sheet_by_index(0)

    # 1) Fila de encabezados de rubros: la que contiene la etiqueta buscada.
    fila_rubros = next(r for r in range(hoja.nrows)
                       if any(_texto(v).startswith(etiqueta_rubro) for v in hoja.row_values(r)))
    encabezados = [_texto(v) for v in hoja.row_values(fila_rubros)]
    col_total = encabezados.index("Total")
    col_rubro = next(c for c, v in enumerate(encabezados) if v.startswith(etiqueta_rubro))

    # 2) Fila de años: la siguiente que dice "Año AAAA" debajo de "Total".
    fila_anios = next(r for r in range(fila_rubros + 1, hoja.nrows)
                      if _texto(hoja.cell_value(r, col_total)).startswith("Año"))

    def anio(fila, col):
        return int(re.search(r"\d{4}", _texto(hoja.cell_value(fila, col))).group())

    # Cada bloque tiene dos columnas de valores: año corriente y año anterior.
    anios = [anio(fila_anios, col_total), anio(fila_anios, col_total + 1)]
    if anios != [anio(fila_anios, col_rubro), anio(fila_anios, col_rubro + 1)]:
        raise ValueError(f"{ruta.name}: los años de 'Total' y de '{etiqueta_rubro}' no coinciden")

    # 3) Filas de meses (Ene ... Dic) y sus valores.
    datos = {}
    for r in range(fila_anios + 1, hoja.nrows):
        mes = next((_texto(v) for v in hoja.row_values(r)[:3] if _texto(v) in MESES_ABREV), None)
        if mes is None:
            continue
        for desplazamiento, anio_col in enumerate(anios):
            total = hoja.cell_value(r, col_total + desplazamiento)
            rubro = hoja.cell_value(r, col_rubro + desplazamiento)
            if isinstance(total, float) and isinstance(rubro, float):  # meses sin dato vienen vacíos
                fecha = pd.Timestamp(anio_col, MESES_ABREV.index(mes) + 1, 1)
                datos[fecha] = {"total": total, "rubro": rubro}

    return pd.DataFrame.from_dict(datos, orient="index").sort_index()


def leer_ica_anual(ruta: Path, etiqueta_rubro: str) -> pd.DataFrame:
    """Lee exp_gr_80_AA.xls o imp_uso_econ_80_AA.xls (anual desde 1980, en miles de USD).

    El archivo está armado en bloques de nueve años, uno debajo del otro; los años
    provisorios vienen marcados con asterisco ("2025*") y los estimados con "e". Devuelve una
    tabla anual (índice = año) con `total` y `rubro` en millones de USD y la marca `provisorio`
    (True si el año tiene cualquiera de las dos marcas).
    """
    hoja = xlrd.open_workbook(ruta).sheet_by_index(0)
    patron_anio = re.compile(r"^(\d{4})(\.0)?([*e]?)$")  # "2025*" = provisorio, "2014e" = estimado

    datos: dict[int, dict] = {}
    anios_bloque = None
    for r in range(hoja.nrows):
        fila = hoja.row_values(r)
        primera = _texto(fila[0])

        if primera in ("Rubros", "Usos"):        # empieza un bloque nuevo
            anios_bloque = None
            continue
        if anios_bloque is None:                  # la primera fila con años define el bloque
            marcas = [patron_anio.match(_texto(v)) for v in fila[1:]]
            if any(marcas):
                anios_bloque = [(int(m.group(1)), m.group(3) != "") if m else None for m in marcas]
            continue

        if primera.startswith("Total general"):
            clave = "total"
        elif primera.startswith(etiqueta_rubro):
            clave = "rubro"
        else:
            continue
        for anio_info, valor in zip(anios_bloque, fila[1:]):
            if anio_info and isinstance(valor, float):
                anio, provisorio = anio_info  # True si tiene marca * o e
                if clave in datos.get(anio, {}):
                    raise ValueError(f"{ruta.name}: el año {anio} aparece dos veces")
                datos.setdefault(anio, {})[clave] = valor / 1000  # miles -> millones de USD
                datos[anio]["provisorio"] = provisorio

    return pd.DataFrame.from_dict(datos, orient="index").sort_index()


# ---------------------------------------------------------------------------------------------
# Informes técnicos del ICA (uno por mes) y sus cuadros
# ---------------------------------------------------------------------------------------------
# Listado oficial de informes técnicos del ICA ("Ver informes técnicos anteriores").
PAGINA_INFORMES_ICA = URL_INDEC + "/Institucional/Indec/InformesTecnicos/40"

MESES_NOMBRE = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                "septiembre", "octubre", "noviembre", "diciembre"]


def listar_informes_ica(nombre_html: str) -> tuple[pd.DataFrame, list[dict]]:
    """Devuelve una tabla con los informes técnicos del ICA publicados.

    Columnas: fecha_publicacion, url_pdf, url_cuadros, url_interactivo.
    El Excel de cuadros se llama ica_cuadros_DD_MM_AA.xls (fecha de publicación) y la versión
    interactiva usa el mismo código que el PDF (ica_MM_AA<código>.pdf -> ica_d_MM_AA<código>/).
    """
    registro = descargar(PAGINA_INFORMES_ICA, CARPETA / nombre_html)
    html = (RAIZ / registro["archivo"]).read_text(encoding="utf-8", errors="replace")

    filas, inicio_bloque = [], 0
    for enlace in re.finditer(r"ica_(\d{2})_(\d{2})([0-9A-F]+)\.pdf", html):
        # La fecha de publicación aparece en el texto del bloque anterior al enlace:
        # "19/10/2026. Intercambio comercial argentino ...". Se sacan las etiquetas HTML sin dejar
        # espacios (a veces cortan palabras) y se aceptan mayúsculas y saltos de línea.
        bloque = re.sub(r"<[^>]+>", "", html[inicio_bloque:enlace.start()])
        fechas = re.findall(r"(\d{1,2})/(\d{1,2})/(\d{4})\.?\s*Intercambio\s+comercial", bloque, flags=re.IGNORECASE)
        inicio_bloque = enlace.end()
        if not fechas:
            continue  # sin fecha legible no se puede armar el nombre del Excel de cuadros
        dia, mes, anio = (int(x) for x in fechas[-1])
        codigo = enlace.group(0)[:-4]  # ica_MM_AA<código>
        filas.append({
            "fecha_publicacion": pd.Timestamp(anio, mes, dia),
            "url_pdf": f"{URL_INDEC}/uploads/informesdeprensa/{codigo}.pdf",
            "url_cuadros": f"{URL_INDEC}/ftp/cuadros/economia/ica_cuadros_{dia:02d}_{mes:02d}_{anio % 100:02d}.xls",
            "url_interactivo": f"{URL_INDEC}/ftp/ica_digital/{codigo.replace('ica_', 'ica_d_')}/",
        })
    tabla = pd.DataFrame(filas).drop_duplicates("fecha_publicacion").sort_values("fecha_publicacion")
    return tabla.reset_index(drop=True), [registro]


def _hoja_por_titulo(libro: xlrd.book.Book, texto: str) -> xlrd.sheet.Sheet:
    """Busca la hoja cuyo título (primeras filas, primera columna) contiene `texto`.
    El número de cuadro cambia entre informes (por ejemplo, c7 en enero y c8 el resto del año)."""
    for hoja in libro.sheets():
        if any(texto in _texto(hoja.cell_value(r, 0)) for r in range(min(3, hoja.nrows))):
            return hoja
    raise ValueError(f"No hay ninguna hoja con '{texto}' en el título")


def leer_cuadro_capitulo27(ruta: Path) -> dict:
    """Lee la balanza comercial del capítulo 27 de la NCM de un Excel de cuadros del ICA.

    Devuelve un diccionario con:
        mes: primer día del mes del informe (por ejemplo, 2026-09-01)
        mes_actual / mes_anterior: {"expo", "impo", "saldo"} del mes del informe y del mismo mes
            del año anterior (este último ya revisado), en millones de USD
        acumulado: {"hasta_mes", "actual", "anterior"} con los acumulados del año en curso y
            del anterior (en los informes de enero, el acumulado es el mismo mes).
    """
    hoja = _hoja_por_titulo(xlrd.open_workbook(ruta), "capítulo 27")
    fila_periodo = next(r for r in range(hoja.nrows) if _texto(hoja.cell_value(r, 0)).startswith("Principales"))
    mes_nombre = _texto(hoja.cell_value(fila_periodo, 2)).lower()
    anio_actual = int(re.search(r"\d{4}", _texto(hoja.cell_value(fila_periodo + 1, 2))).group())
    anio_anterior = int(re.search(r"\d{4}", _texto(hoja.cell_value(fila_periodo + 1, 3))).group())
    if anio_anterior != anio_actual - 1:
        raise ValueError(f"{ruta.name}: años inesperados {anio_actual} y {anio_anterior}")
    numero_mes = MESES_NOMBRE.index(mes_nombre) + 1

    def fila(*prefijos):
        return next(r for r in range(hoja.nrows) if _texto(hoja.cell_value(r, 0)).startswith(prefijos))

    # El saldo se llama "Balanza comercial" (y en informes anteriores a 2025, "Exportaciones netas").
    filas = {"saldo": fila("Balanza comercial", "Exportaciones netas"), "expo": fila("Exportación del capítulo 27"),
             "impo": fila("Importación del capítulo 27")}

    def valores(columna):
        return {clave: float(hoja.cell_value(r, columna)) for clave, r in filas.items()}

    resultado = {"mes": pd.Timestamp(anio_actual, numero_mes, 1),
                 "mes_actual": valores(2), "mes_anterior": valores(3)}
    # El encabezado del acumulado dice "Acumulado hasta ..." (en febrero, "Primer bimestre").
    tiene_acumulado = hoja.ncols >= 8 and _texto(hoja.cell_value(fila_periodo, 6)) != ""
    if tiene_acumulado:
        resultado["acumulado"] = {"hasta_mes": numero_mes, "actual": valores(6), "anterior": valores(7)}
    elif numero_mes == 1:  # los informes de enero no traen columnas de acumulado
        resultado["acumulado"] = {"hasta_mes": 1, "actual": valores(2), "anterior": valores(3)}
    else:
        raise ValueError(f"{ruta.name}: falta el acumulado en un informe que no es de enero")
    return resultado


def leer_cuadro1_acumulado(ruta: Path) -> dict:
    """Lee del cuadro 1 del Excel de cuadros el acumulado del año (año en curso y anterior).

    El mes del informe es el último mes con dato del año en curso. La fila del acumulado se
    llama distinto según ese mes:
        enero      -> no hay fila aparte: el acumulado es la fila "Enero"
        febrero    -> "Total bimestre" (en el PDF, "Primer bimestre")
        diciembre  -> "Total anual" (no hay fila "Acumulado")
        el resto   -> "Acumulado hasta <mes>"
    Control: el acumulado tiene que ser igual a la suma de los meses de enero al mes del informe,
    en los dos años; si no, falla (así no se toma una fila equivocada sin aviso). La tolerancia es
    0,5 por mes sumado, porque hasta 2024 los cuadros venían redondeados a millones y "los totales
    por suma pueden no coincidir por redondeo" (nota del cuadro); una fila equivocada difiere en miles.
    Devuelve {"mes", "actual": {"expo", "impo", "saldo"}, "anterior": {...}} en millones de USD.
    """
    hoja = _hoja_por_titulo(xlrd.open_workbook(ruta), "Cuadro 1.")
    etiquetas = [_texto(hoja.cell_value(r, 1)) for r in range(hoja.nrows)]
    filas_mes = {MESES_NOMBRE.index(e.lower()) + 1: r for r, e in enumerate(etiquetas) if e.lower() in MESES_NOMBRE}
    meses_con_dato = sorted(m for m, r in filas_mes.items() if isinstance(hoja.cell_value(r, 2), float))
    numero_mes = meses_con_dato[-1]
    if meses_con_dato != list(range(1, numero_mes + 1)):
        raise ValueError(f"{ruta.name}: meses con dato inesperados en el cuadro 1: {meses_con_dato}")
    anio = next(int(re.match(r"\d{4}", _texto(hoja.cell_value(r, 2))).group()) for r in range(2, 10)
                if re.match(r"\d{4}", _texto(hoja.cell_value(r, 2))))

    if numero_mes == 1:
        fila = filas_mes[1]
    else:
        prefijos = ("Acumulado", "Total bimestre", "Primer bimestre") + (("Total anual",) if numero_mes == 12 else ())
        fila = next(r for r, e in enumerate(etiquetas) if e.startswith(prefijos))

    # Columnas: exportaciones (2 = año en curso, 3 = anterior), importaciones (6, 7), saldo (10, 11).
    columnas = {"actual": {"expo": 2, "impo": 6, "saldo": 10}, "anterior": {"expo": 3, "impo": 7, "saldo": 11}}
    resultado = {"mes": pd.Timestamp(anio, numero_mes, 1)}
    for clave, cols in columnas.items():
        resultado[clave] = {flujo: float(hoja.cell_value(fila, c)) for flujo, c in cols.items()}
        for flujo, c in cols.items():
            suma = sum(float(hoja.cell_value(filas_mes[m], c)) for m in range(1, numero_mes + 1))
            if abs(suma - resultado[clave][flujo]) > 0.5 * numero_mes:
                raise ValueError(f"{ruta.name}: la fila '{etiquetas[fila]}' no es la suma de enero a "
                                 f"{MESES_NOMBRE[numero_mes - 1]} ({clave}, {flujo}: {resultado[clave][flujo]} vs {suma})")
    return resultado


def _hoja_por_patron(libro: xlrd.book.Book, patron: str) -> xlrd.sheet.Sheet:
    """Busca la única hoja cuyo título (celda A1) cumple la expresión regular `patron`."""
    hojas = [h for h in libro.sheets() if h.nrows and re.search(patron, _texto(h.cell_value(0, 0)))]
    if len(hojas) != 1:
        raise ValueError(f"Se esperaba 1 hoja con título '{patron}' y hay {len(hojas)}")
    return hojas[0]


def _leer_mes_y_acumulado(hoja: xlrd.sheet.Sheet, filas: dict[str, int], nombre: str) -> dict:
    """Lee, de un cuadro con columnas "mes | acumulado", los valores de las filas pedidas.

    Estructura de estos cuadros: la columna 3 tiene el mes del informe (año en curso) y la 4, el
    mismo mes del año anterior; la 6 y la 7, el acumulado de los dos años. Arriba de los números
    hay una fila con el nombre del mes, otra con los años y otra con la unidad.
    """
    fila_mes = next(r for r in range(10) if _texto(hoja.cell_value(r, 3)).lower() in MESES_NOMBRE)
    numero_mes = MESES_NOMBRE.index(_texto(hoja.cell_value(fila_mes, 3)).lower()) + 1
    anios = [int(re.match(r"\d{4}", _texto(hoja.cell_value(fila_mes + 1, c))).group()) for c in (3, 4)]
    if anios[1] != anios[0] - 1:
        raise ValueError(f"{nombre}: años inesperados {anios}")
    if not _texto(hoja.cell_value(fila_mes + 2, 3)).startswith("Millones"):
        raise ValueError(f"{nombre}: se esperaban millones de USD y dice '{hoja.cell_value(fila_mes + 2, 3)}'")

    def valores(columna):
        return {clave: float(hoja.cell_value(r, columna)) for clave, r in filas.items()}

    resultado = {"mes": pd.Timestamp(anios[0], numero_mes, 1), "mes_actual": valores(3), "mes_anterior": valores(4)}
    # El encabezado del acumulado dice "Acumulado hasta ...", "Primer bimestre" o, en diciembre de
    # algunos años, "Doce meses".
    if hoja.ncols >= 8 and _texto(hoja.cell_value(fila_mes, 6)).startswith(("Acumulado", "Primer", "Doce meses")):
        resultado["acumulado"] = {"actual": valores(6), "anterior": valores(7)}
    elif numero_mes == 1:  # en enero, el acumulado es el mismo mes
        resultado["acumulado"] = {"actual": valores(3), "anterior": valores(4)}
    else:
        raise ValueError(f"{nombre}: falta el acumulado en un informe que no es de enero")
    return resultado


def leer_cuadro_rubros_usos(ruta: Path) -> dict:
    """Lee del Excel de cuadros de un informe del ICA las exportaciones de Combustibles y energía
    (CyE) y las importaciones de Combustibles y lubricantes (CyL), con sus totales.

    Cuadros que lee (el número cambia entre informes, por eso se buscan por título):
        - "Exportaciones por grandes rubros y principales subrubros" (en 2025, "por principales
          rubros y principales subrubros"; en enero de 2024, "por principales rubros."): fila
          "Total" y fila del gran rubro "Combustibles y energía (CyE)".
        - "Importaciones, según usos económicos, grandes categorías económicas (GCE) y agregados
          especiales": fila "Total general" y fila del uso económico "Combustibles y lubricantes"
          (columna 1; las filas de la columna 2 son subcategorías GCE y no se usan).
    Devuelve {"mes", "hojas", "mes_actual", "mes_anterior", "acumulado": {"actual", "anterior"}},
    cada uno con expo_total, expo_cye, impo_total e impo_cyl en millones de USD ("hojas" dice de
    qué hoja del Excel sale cada flujo).
    """
    libro = xlrd.open_workbook(ruta)
    expo = _hoja_por_patron(libro, r"^Cuadro \d+\. Exportaciones por (grandes|principales) rubros(\.| y principales subrubros)")
    impo = _hoja_por_patron(libro, r"^Cuadro \d+\. - Importaciones, según usos económicos")

    def fila(hoja, columna, prefijo):
        return next(r for r in range(hoja.nrows) if _texto(hoja.cell_value(r, columna)).startswith(prefijo))

    leido_expo = _leer_mes_y_acumulado(expo, {"expo_total": fila(expo, 0, "Total"),
                                              "expo_cye": fila(expo, 1, "Combustibles y energía")}, ruta.name)
    leido_impo = _leer_mes_y_acumulado(impo, {"impo_total": fila(impo, 0, "Total general"),
                                              "impo_cyl": fila(impo, 1, "Combustibles y lubricantes")}, ruta.name)
    if leido_expo["mes"] != leido_impo["mes"]:
        raise ValueError(f"{ruta.name}: el cuadro de exportaciones y el de importaciones son de meses distintos")
    return {
        "mes": leido_expo["mes"],
        "hojas": {"expo": expo.name, "impo": impo.name},  # por ejemplo c12 y c14, para citar el cuadro
        "mes_actual": {**leido_expo["mes_actual"], **leido_impo["mes_actual"]},
        "mes_anterior": {**leido_expo["mes_anterior"], **leido_impo["mes_anterior"]},
        "acumulado": {clave: {**leido_expo["acumulado"][clave], **leido_impo["acumulado"][clave]}
                      for clave in ("actual", "anterior")},
    }


def leer_capitulo_anual(ruta: Path) -> dict[str, dict[int, float]]:
    """Lee un cuadro anual por capítulos de la NCM (exp_ncm_AA_AA.xls o imp_ncm_AA_AA.xls).

    Devuelve {"capitulo27": {año: valor}, "total": {año: valor}}: la fila del capítulo 27 (en
    estos cuadros se llama "Combustibles y aceites minerales...") y la fila "Total".
    Los cuadros vienen en millones de USD, pero alguno no lo dice en el encabezado: por eso se
    devuelve también el total, para que quien lo use lo compare con el total anual oficial
    (si coinciden, la unidad es la correcta).
    """
    hoja = xlrd.open_workbook(ruta).sheet_by_index(0)
    patron_anio = re.compile(r"^(\d{4})(\.0)?[*e]?$")  # "2024*" = provisorio, "2014e" = estimado

    anios, resultado = None, {}
    for r in range(hoja.nrows):
        fila = hoja.row_values(r)
        if anios is None and any(patron_anio.match(_texto(v)) for v in fila[1:]):
            anios = [int(patron_anio.match(_texto(v)).group(1)) if patron_anio.match(_texto(v)) else None
                     for v in fila[1:]]
            continue
        if not anios:
            continue
        for clave, prefijo in (("total", "Total"), ("capitulo27", "Combustibles")):
            if _texto(fila[0]).startswith(prefijo) and clave not in resultado:
                resultado[clave] = {a: float(v) for a, v in zip(anios, fila[1:]) if a and isinstance(v, float)}
    if set(resultado) != {"total", "capitulo27"}:
        raise ValueError(f"{ruta.name}: no se encontraron las filas 'Total' y del capítulo 27")
    return resultado


def leer_rubros_usos_mensual(ruta: Path) -> pd.DataFrame:
    """Lee serie_rubros_usos_mensual.xlsx (versión interactiva del informe, desde 2004).

    Viene en formato largo (año, mes, comercio, rubro_uso, valor en USD). Devuelve una tabla
    mensual en millones de USD con expo_total_musd, expo_cye_musd, impo_total_musd e
    impo_cyl_musd. Los totales son la suma de todos los rubros o usos (incluido "Resto").
    """
    largo = pd.read_excel(ruta, dtype={"año": int, "mes": int})
    largo["fecha"] = pd.to_datetime(dict(year=largo["año"], month=largo["mes"], day=1))
    largo["valor"] = largo["valor"] / 1e6  # USD -> millones de USD

    expo = largo[largo["comercio"] == "Exportaciones"]
    impo = largo[largo["comercio"] == "Importaciones"]
    es_cye = expo["rubro_uso"].str.startswith("Combustibles y energía")
    es_cyl = impo["rubro_uso"].str.startswith("Combustibles y lubricantes")
    tabla = pd.DataFrame({
        "expo_total_musd": expo.groupby("fecha")["valor"].sum(),
        "expo_cye_musd": expo[es_cye].groupby("fecha")["valor"].sum(),
        "impo_total_musd": impo.groupby("fecha")["valor"].sum(),
        "impo_cyl_musd": impo[es_cyl].groupby("fecha")["valor"].sum(),
    })
    tabla.index.name = "fecha"
    return tabla
