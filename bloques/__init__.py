"""
Armadores, uno o más por bloque (bloques/<bloque>/<armador>.py). Aplican los criterios validados
(criterios-metodologicos.md), arman las series y corren los controles. No bajan nada ni leen crudos
directamente: usan los lectores.

Cada armador declara SERIES, y opcionalmente AUXILIARES, DEPENDE_DE y FORMATO, y una función armar()
(el detalle está en comun/catalogo.py). actualizar.py los encuentra, los corre en orden y escribe sus
series en datos/series/<bloque>/ solo si ningún control bloqueante falla sin excepción aprobada.
Los armadores actuales (series/ y la parte genérica de la nota "La vuelta del gas") se mudan acá en
los Pasos 3b y 3c.
"""
