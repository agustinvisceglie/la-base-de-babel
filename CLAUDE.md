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
- Fuentes permitidas (regla 4 del instructivo de trabajo):
  - **Permitidas:** oficiales argentinas; organismos oficiales extranjeros e internacionales (BLS, EIA, Banco Mundial, FMI); y **solo** las fuentes de mercado aprobadas (Índice CCL de A3 Mercados, Índice CCL de BYMA, precios de ADR y de acciones locales para el CCL anterior a 2020), siempre rotuladas "no oficial".
  - **Excepciones aprobadas después:** la Encuesta de Expectativas de Inflación y el Índice de Confianza del Consumidor de la UTDT (sección 21 de los criterios, rótulo "no oficial (académica)"). Caución, repo y tasas de Lecap cortas: series de tasas con licencia verificada (sección 19). Índices privados, breakevens y futuros: solo como `uso = control` y con licencia verificada (secciones 17, 19 y 21).
  - **Sin licencia clara:** si una fuente no la tiene o sus condiciones de uso prohíben la descarga automática, frenar e informarlo.
  - **Prohibido:** nada del empleador actual de Agustín ni de sus clientes, y la cuenta de GitHub de trabajo no aparece en ningún lado.
  - Nunca datos internos de empresas ni datos que no sean públicos.
- Toda serie tiene documentado: organismo, ID o URL exacta, unidad, frecuencia y fecha de descarga.
- Las unidades van en el nombre de la columna (`_musd` = millones de USD, `_kbbl_d` = miles de barriles por día, `_mm3_d` = millones de m3 por día).
- Las descargas originales se guardan como versiones comprimidas en `datos/crudos/<organismo>/versiones/` (no van a Git; respaldo en el OneDrive personal) y nunca se modifican; su hash queda en `datos/registros/versiones_crudos.csv`. Las series limpias las arma `actualizar.py` en `datos/series/<bloque>/`, con su fila en `catalogo_series.csv`, y la validación de cada bloque va a `datos/validacion/<bloque>/`.
- Solo estimaciones aprobadas por Agustín, marcadas en la columna 'fuente', con la aclaración en toda nota o gráfico que las use.

## Controles obligatorios antes de dar por bueno un número
1. Unidades: millones vs. miles, m3 vs. barriles, mensual vs. acumulado.
2. Tipo de variación: mensual, interanual o acumulada; decirlo siempre.
3. Cambios de base y empalmes de series: documentar cómo se hicieron.
4. Valores nominales vs. reales: si se deflacta, decir con qué índice.
5. Contrastar al menos un dato por serie contra el informe oficial publicado (ej.: el informe técnico del INDEC) y dejar la comparación en el informe de validación.

## Reglas de trabajo
- No decidir criterios económicos: qué elecciones abarca está en la regla 2 de "Reglas permanentes". Frenar, presentar las opciones con sus pros y contras, y esperar la decisión de Agustín (que la valida en el chat del proyecto contra al menos 5 fuentes profesionales).
- Todo lo que se entrega es auditado en el chat del proyecto: citar URL/ID y cuadro de cada dato, separar lo verificado de lo supuesto, y antes de afirmar que un dato no existe listar todas las fuentes revisadas.
- Seguir la convención del INDEC, la Secretaría de Energía, el BCRA y las consultoras, salvo razón fuerte y documentada.

## Criterios económicos: fuente de verdad
- Los criterios económicos decididos y validados están en `criterios-metodologicos.md` (secciones 1 a 24, con las fuentes profesionales que respaldan cada uno), en la carpeta de trabajo de Substack (OneDrive), fuera de este repositorio. **Es la fuente de verdad**: ante una duda, manda ese archivo.
- La hoja de ruta del trabajo en este repositorio (pasos, reglas permanentes y formato de informe) es `instructivo-code.md`, en la misma carpeta.

## Reglas permanentes (del instructivo de trabajo; valen para todos los pasos)
1. **Un paso por vez.** Al terminar un paso, frenar y entregar el informe. El siguiente arranca recién cuando Agustín lo indica, después de la auditoría.
2. **No decidir criterios económicos.** Si aparece una elección de definición, serie, agrupación, método, período, unidad, empalme o tratamiento de un dato faltante que **no** esté resuelta en `criterios-metodologicos.md`, frenar y presentarla con sus opciones. No elegir "la más razonable". Las decisiones ya tomadas **no se reabren**: si alguna parece mal, se dice en el informe, pero se aplica tal cual.
3. **Git:**
   - commit al final de cada paso, con un mensaje claro;
   - **nunca push** sin el ok explícito de Agustín;
   - nunca borrar archivos ni reescribir el historial;
   - `git pull` antes de empezar si hubo trabajo en la otra PC (la notebook no se usa con Code).
4. **Fuentes:** solo las de la lista de "Datos" (arriba), con sus rótulos, sus excepciones y lo prohibido.
5. **Reproducibilidad:**
   - todo número sale de un crudo versionado y de código;
   - nada se tipea a mano, salvo los registros de normas (hitos, regímenes, derechos de exportación), que llevan la norma y el enlace en cada fila.
6. **Controles bloqueantes:**
   - un control que falla frena el armado del bloque, salvo que haya una excepción aprobada en `datos/registros/excepciones.csv`;
   - las excepciones las propone Code y las aprueba Agustín. Code **no** las da de alta por su cuenta.
7. **Nada de "parches":** si para que algo cierre hace falta tocar un dato puntual, eso es una decisión. Frenar.
8. **Descargas grandes:** si un paso necesita bajar más de 1 GB en total, avisar el tamaño estimado antes de bajarlo y esperar el ok de Agustín. Si el portal no informa la fecha de publicación de un recurso, no se baja a ciegas: frenar.
9. **Credenciales:** contraseñas, códigos, CAPTCHAs, autenticaciones y aceptación de términos los resuelve Agustín. Si aparecen, frenar.
10. **Contradicciones:** si una instrucción contradice el instructivo o los criterios, frenar y señalarlo; no elegir cuál vale.

## Forma de trabajar
- Antes de hacer `git push`, mostrarle a Agustín qué cambió y esperar su ok.
- Commits chicos, con mensajes en español que digan qué se hizo.
- Si una fuente no está disponible o un dato no cierra, decirlo; no inventar ni estimar sin aprobación.
- Los CSV para gráficos (Datawrapper) usan punto decimal, coma como separador de columnas y una fila por fecha. Datawrapper después los muestra con formato argentino.
