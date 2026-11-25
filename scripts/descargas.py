"""
Descargas genéricas (compatibilidad): desde el Paso 3a todo esto vive en comun/descargas.py.

Qué hace: reexporta las funciones y constantes de comun/descargas.py con los mismos nombres, para que
    el código de scripts/ y series/ siga funcionando sin cambios hasta que se migre a lectores/ y
    bloques/ (Pasos 3b y 3c). Así hay una sola implementación que escribe el registro de versiones
    (datos/registros/versiones_crudos.csv) y una sola forma de guardar versiones (comprimidas, .gz,
    con el hash del original).
Fuentes: cualquiera.
Genera: lo mismo que comun/descargas.py.
"""

from comun.descargas import (CRUDOS, ENCABEZADOS, PROCESADOS, RAIZ, REGISTRO_VERSIONES, ZONA_HORARIA,  # noqa: F401
                             _registro, descargar, guardar_registro, guardar_version)
