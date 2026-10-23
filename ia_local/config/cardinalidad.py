from __future__ import annotations


# ============================================================
# IA-LLM004-D0
# POLÍTICA GLOBAL DE CARDINALIDAD
# ============================================================
#
# Este módulo es la única autoridad interna de ia_local
# para límites de resultados.
#
# No depende de settings.py ni de configuración del proyecto
# anfitrión.
#
# Objetivo:
#
#   - mantener ia_local plug-and-play;
#   - evitar números mágicos repartidos por varios módulos;
#   - permitir cambiar la política modificando únicamente
#     estos valores.
#
# ============================================================


# Cantidad de registros mostrados cuando el usuario no pide
# explícitamente una cantidad.
LIMITE_MUESTRA_PREDETERMINADO = 20


# Máximo que debe materializarse para una respuesta interactiva.
LIMITE_MAXIMO_INTERACTIVO = 100


# Máxima cantidad explícita que una consulta natural puede pedir
# para una respuesta interactiva.
LIMITE_MAXIMO_SOLICITABLE = 100
