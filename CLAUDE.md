# Reglas del proyecto La Base de Babel

Repositorio de datos y código de "Sobre Modelos y Tumbas", publicación de Agustín Visceglie (economista, UBA) sobre macroeconomía y energía argentina.

## Para qué existe
- Es el portfolio público de Agustín para pasar a un puesto de analista macro / coyuntura con la energía como diferencial. Lo van a mirar reclutadores y economistas: la prolijidad y la trazabilidad de los números importan tanto como el resultado.
- Publicación: sobremodelosytumbas.substack.com. Subtítulo: "Sin héroes ni milagros: macro y energía argentina". Línea editorial neutral: sin militancia, sin recomendaciones de inversión, sin opinar sobre empresas puntuales.
- Secciones: "Coyuntura y Barbarie" (coyuntura mensual), "El Pozo y el Péndulo" (energía, Vaca Muerta y su impacto macro: balanza, reservas, cuentas públicas) y "La Base de Babel" (este repositorio: datos, métodos y código).
- Ritmo: 2 notas por mes. Cada nota que usa datos tiene su carpeta en `notas/` y tiene que poder reproducirse con un comando.
- Agustín revisa el código leyéndolo: priorizá código claro y comentado por sobre código ingenioso.

## Idioma y estilo
- Código, comentarios, nombres de archivos y columnas en español, sin tildes ni ñ en los nombres (ej.: `exportaciones_energia_musd`).
- Cada script empieza con un comentario de qué hace, qué fuentes usa y qué genera.

## Datos
- Solo fuentes públicas oficiales: INDEC, BCRA, Secretaría de Energía, API de Series de Tiempo (apis.datos.gob.ar/series). Nunca datos privados ni de empresas.
- Toda serie tiene documentado: organismo, ID o URL exacta, unidad, frecuencia y fecha de descarga.
- Las unidades van en el nombre de la columna (`_musd` = millones de USD, `_kbbl_d` = miles de barriles por día, `_mm3_d` = millones de m3 por día).
- Las descargas originales van a `datos/crudos/` y no se modifican; la limpieza genera archivos nuevos en `datos/procesados/`.
- Cuando una serie tenga valores estimados (por ejemplo, por secreto estadístico o por faltantes), marcarlos en una columna 'fuente' y, en toda nota o gráfico que los use o los cite, incluir una aclaración que diga qué se estimó y cómo.

## Controles obligatorios antes de dar por bueno un número
1. Unidades: millones vs. miles, m3 vs. barriles, mensual vs. acumulado.
2. Tipo de variación: mensual, interanual o acumulada; decirlo siempre.
3. Cambios de base y empalmes de series: documentar cómo se hicieron.
4. Valores nominales vs. reales: si se deflacta, decir con qué índice.
5. Contrastar al menos un dato por serie contra el informe oficial publicado (ej.: el informe técnico del INDEC) y dejar la comparación en el informe de validación.

## Forma de trabajar
- Antes de hacer `git push`, mostrarle a Agustín qué cambió y esperar su ok.
- Commits chicos, con mensajes en español que digan qué se hizo.
- Si una fuente no está disponible o un dato no cierra, decirlo; no inventar ni estimar sin avisar.
- Los CSV para gráficos (Datawrapper) usan punto decimal, coma como separador de columnas y una fila por fecha. Datawrapper después los muestra con formato argentino.
