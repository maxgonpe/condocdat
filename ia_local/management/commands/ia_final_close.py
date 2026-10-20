from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
)

from ia_local.models import (
    IAHistorialConsulta,
)

from ia_local.services.final.formateador_respuesta import (
    responder_consulta,
)

from ia_local.services.final.politica_respuesta import (
    aplicar_politica_respuesta,
)

from ia_local.services.final.correccion_semantica import (
    proponer_correccion_semantica,
)


VERSION = "IA-FINAL010-v1"


class Command(BaseCommand):

    help = (
        "IA-FINAL010 - Auditoría integral "
        "y cierre de la fase FINAL."
    )

    def _consulta(
        self,
        pregunta: str,
    ):

        respuesta = responder_consulta(
            pregunta
        )

        return aplicar_politica_respuesta(
            pregunta=pregunta,
            respuesta=respuesta,
        )

    def handle(
        self,
        *args,
        **options,
    ):

        pruebas = []

        def registrar(
            nombre,
            ok,
            detalle=None,
        ):

            pruebas.append(
                {
                    "nombre":
                        nombre,

                    "ok":
                        bool(
                            ok
                        ),

                    "detalle":
                        detalle,
                }
            )

        # ====================================================
        # CONSULTA SIMPLE
        # ====================================================

        r = self._consulta(
            "listar documentos"
        )

        registrar(
            "FINAL_CONSULTA_SIMPLE",
            (
                r.get("ok") is True
                and r.get(
                    "clasificacion"
                )
                == "resuelta_ejecutada"
                and r.get(
                    "ejecutado"
                )
                is True
                and isinstance(
                    r.get(
                        "registros"
                    ),
                    list,
                )
            ),
            {
                "estado":
                    r.get(
                        "estado"
                    ),

                "clasificacion":
                    r.get(
                        "clasificacion"
                    ),

                "total":
                    r.get(
                        "total"
                    ),
            },
        )

        # ====================================================
        # AND
        # ====================================================

        r = self._consulta(
            (
                "listar documentos cuyo tema contiene "
                "estructura y codigo contiene ODATA"
            )
        )

        registrar(
            "FINAL_CONSULTA_AND",
            (
                isinstance(
                    r,
                    dict,
                )
                and r.get(
                    "llm_invocado"
                )
                is False
            ),
            {
                "ok":
                    r.get(
                        "ok"
                    ),

                "estado":
                    r.get(
                        "estado"
                    ),

                "clasificacion":
                    r.get(
                        "clasificacion"
                    ),
            },
        )

        # ====================================================
        # FECHA RELATIVA
        # ====================================================

        r = self._consulta(
            "listar documentos de esta semana"
        )

        registrar(
            "FINAL_FECHA_RELATIVA",
            (
                r.get(
                    "ejecutado"
                )
                is True
                and r.get(
                    "clasificacion"
                )
                == "resuelta_ejecutada"
            ),
            {
                "total":
                    r.get(
                        "total"
                    ),

                "modelo":
                    r.get(
                        "modelo"
                    ),
            },
        )

        # ====================================================
        # RELACIONAL
        # ====================================================

        r = self._consulta(
            "contar proyectos de documentos"
        )

        registrar(
            "FINAL_RELACIONAL",
            (
                r.get(
                    "ejecutado"
                )
                is True
                and r.get(
                    "tipo"
                )
                == "conteo"
                and isinstance(
                    r.get(
                        "total"
                    ),
                    int,
                )
            ),
            {
                "total":
                    r.get(
                        "total"
                    ),

                "clasificacion":
                    r.get(
                        "clasificacion"
                    ),
            },
        )

        # ====================================================
        # CONSULTA SIN RESULTADOS
        # ====================================================

        r = self._consulta(
            (
                "listar documentos cuyo tema contiene "
                "ZZZ_FINAL010_INEXISTENTE"
            )
        )

        registrar(
            "FINAL_LISTA_VACIA",
            (
                r.get(
                    "ejecutado"
                )
                is True
                and r.get(
                    "total"
                )
                == 0
            ),
            {
                "total":
                    r.get(
                        "total"
                    ),

                "respuesta":
                    r.get(
                        "respuesta"
                    ),
            },
        )

        # ====================================================
        # CAPACIDAD NO EJECUTABLE
        # ====================================================

        r = self._consulta(
            "promedio de number de documentos"
        )

        registrar(
            "FINAL_CAPACIDAD_NO_EJECUTABLE",
            (
                r.get(
                    "ok"
                )
                is False
                and r.get(
                    "clasificacion"
                )
                == "capacidad_no_ejecutable"
                and r.get(
                    "ejecutado"
                )
                is False
            ),
            {
                "clasificacion":
                    r.get(
                        "clasificacion"
                    ),

                "respuesta":
                    r.get(
                        "respuesta"
                    ),
            },
        )

        # ====================================================
        # CONSULTA NO RESUELTA
        # ====================================================

        r = self._consulta(
            "dame lo de ayer"
        )

        registrar(
            "FINAL_CONSULTA_NO_RESUELTA",
            (
                r.get(
                    "ok"
                )
                is False
                and r.get(
                    "clasificacion"
                )
                == "consulta_no_resuelta"
                and r.get(
                    "requiere_aclaracion"
                )
                is True
                and r.get(
                    "ejecutado"
                )
                is False
            ),
            {
                "clasificacion":
                    r.get(
                        "clasificacion"
                    ),

                "requiere_aclaracion":
                    r.get(
                        "requiere_aclaracion"
                    ),
            },
        )

        # ====================================================
        # ENTIDAD INVENTADA
        # ====================================================

        r = self._consulta(
            "listar cosa inventada"
        )

        registrar(
            "FINAL_SEGURIDAD_ENTIDAD_INVENTADA",
            (
                r.get(
                    "ok"
                )
                is False
                and r.get(
                    "ejecutado"
                )
                is False
                and r.get(
                    "clasificacion"
                )
                == "consulta_no_resuelta"
            ),
            {
                "clasificacion":
                    r.get(
                        "clasificacion"
                    ),
            },
        )

        # ====================================================
        # FINAL008
        # PROPUESTA INVÁLIDA DEBE SER RECHAZADA
        # ====================================================

        propuesta = (
            proponer_correccion_semantica(
                tipo=(
                    "TIPO_FINAL010"
                ),
                expresion=(
                    "prueba seguridad "
                    "final010"
                ),
                datos={},
                motivo=(
                    "Auditoría FINAL010"
                ),
            )
        )

        registrar(
            "FINAL_CORRECCION_SEGURA",
            (
                propuesta.get(
                    "ok"
                )
                is False
                and propuesta.get(
                    "propuesta_creada"
                )
                is False
                and propuesta.get(
                    "llm_invocado"
                )
                is False
            ),
            {
                "estado":
                    propuesta.get(
                        "estado"
                    ),
            },
        )

        # ====================================================
        # FINAL007
        # MODELO DE HISTORIAL
        # ====================================================

        campos_historial = {
            campo.name
            for campo
            in (
                IAHistorialConsulta
                ._meta
                .fields
            )
        }

        prohibidos = {
            "diagnostico",
            "registros",
            "resultado",
            "plan",
            "sql",
        }

        registrar(
            "FINAL_TRAZABILIDAD_COMPACTA",
            not bool(
                campos_historial
                & prohibidos
            ),
            {
                "total_historial":
                    (
                        IAHistorialConsulta
                        .objects
                        .count()
                    ),

                "campos_prohibidos":
                    sorted(
                        campos_historial
                        & prohibidos
                    ),
            },
        )

        # ====================================================
        # LLM
        # ====================================================

        preguntas_llm = [
            "listar documentos",
            "contar proyectos de documentos",
            "promedio de number de documentos",
            "dame lo de ayer",
        ]

        llm_detectado = False

        for pregunta in preguntas_llm:

            resultado = self._consulta(
                pregunta
            )

            if (
                resultado.get(
                    "llm_invocado"
                )
                is True
            ):

                llm_detectado = True

        registrar(
            "FINAL_SIN_LLM",
            not llm_detectado,
            {
                "llm_detectado":
                    llm_detectado,
            },
        )

        # ====================================================
        # RESULTADO GLOBAL
        # ====================================================

        aprobadas = sum(
            1
            for prueba
            in pruebas
            if prueba[
                "ok"
            ]
        )

        total = len(
            pruebas
        )

        fallidas = (
            total
            - aprobadas
        )

        salida = {
            "ok":
                fallidas == 0,

            "version":
                VERSION,

            "estado": (
                "auditoria_final_aprobada"
                if fallidas == 0
                else "auditoria_final_fallida"
            ),

            "total":
                total,

            "aprobadas":
                aprobadas,

            "fallidas":
                fallidas,

            "pruebas":
                pruebas,

            "ejecutado":
                True,

            "llm_invocado":
                False,
        }

        self.stdout.write(
            json.dumps(
                salida,
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )