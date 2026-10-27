"""
ARC003-B05-C01
Caracterizacion del despacho certificado.

No introduce un ejecutor productivo.
No consulta registros ORM.
La autorizacion y la ejecucion son simuladas.
"""

from copy import deepcopy
from unittest.mock import Mock

from django.test import SimpleTestCase

from ia_local.services.host.validador_plan_datos import (
    validar_plan_datos,
)
from ia_local.services.llm.certificador_limitado import (
    certificar_consulta_limitada,
)


PREGUNTA = (
    "¿Cuántos Documentos tienen status igual a ACTIVO?"
)


def despacho_simulado(
    pregunta,
    plan,
    autorizar,
    ejecutar,
):
    """
    Contrato experimental:
      HOST -> certificacion -> autorizacion -> ejecucion simulada.

    Falla cerrado ante errores o alteraciones.
    """

    try:
        if not isinstance(plan, dict):
            return {"ok": False, "estado": "plan_invalido"}

        plan_local = deepcopy(plan)

        # Volver a comprobar la estructura mediante HOST.
        validacion = validar_plan_datos(
            deepcopy(plan_local)
        )

        if (
            not isinstance(validacion, dict)
            or validacion.get("ok") is not True
            or validacion.get("plan_validado") is not True
            or validacion.get("plan") != plan_local
        ):
            return {
                "ok": False,
                "estado": "plan_host_no_validado",
            }

        # La certificacion se recalcula, no se recibe del cliente.
        certificado = certificar_consulta_limitada(
            pregunta,
            deepcopy(plan_local),
        )

        if (
            certificado.get("ok") is not True
            or certificado.get("certificacion_limitada") is not True
            or certificado.get("estado") != "certificado_limitado"
        ):
            return {
                "ok": False,
                "estado": "certificacion_no_disponible",
            }

        # Autorizacion independiente y simulada.
        decision = autorizar(deepcopy(plan_local))

        if decision is not True:
            return {
                "ok": False,
                "estado": "acceso_no_autorizado",
            }

        # Rechazar mutaciones posteriores a la certificacion.
        if plan != plan_local:
            return {
                "ok": False,
                "estado": "plan_modificado",
            }

        # Este ejecutor es un Mock en todas las pruebas.
        resultado = ejecutar(deepcopy(plan_local))

        return {
            "ok": True,
            "estado": "despacho_simulado",
            "resultado": resultado,
        }

    except Exception:
        return {
            "ok": False,
            "estado": "despacho_rechazado",
        }


class TestARC003B05DespachoSimulado(SimpleTestCase):

    def setUp(self):
        propuesta = {
            "modelo": "documents.Document",
            "operacion": "contar",
            "filtros": [{
                "campo": "status",
                "operador": "exact",
                "valor": "ACTIVO",
            }],
            "orden": [],
            "limite": 10,
            "condiciones_no_resueltas": [],
        }

        validacion = validar_plan_datos(propuesta)
        self.assertTrue(validacion["ok"])

        self.plan = validacion["plan"]
        self.ejecutor = Mock(
            return_value={"total": 7}
        )

    def test_01_certificado_y_autorizado(self):
        autorizador = Mock(return_value=True)

        resultado = despacho_simulado(
            PREGUNTA,
            self.plan,
            autorizador,
            self.ejecutor,
        )

        self.assertTrue(resultado["ok"])
        self.assertEqual(
            resultado["estado"],
            "despacho_simulado",
        )
        self.ejecutor.assert_called_once()

    def test_02_sin_autorizacion(self):
        resultado = despacho_simulado(
            PREGUNTA,
            self.plan,
            Mock(return_value=False),
            self.ejecutor,
        )

        self.assertFalse(resultado["ok"])
        self.assertEqual(
            resultado["estado"],
            "acceso_no_autorizado",
        )
        self.ejecutor.assert_not_called()

    def test_03_plan_alterado(self):
        alterado = deepcopy(self.plan)
        alterado["filtros"][0]["valor"] = "CERRADO"

        resultado = despacho_simulado(
            PREGUNTA,
            alterado,
            Mock(return_value=True),
            self.ejecutor,
        )

        self.assertFalse(resultado["ok"])
        self.ejecutor.assert_not_called()

    def test_04_negacion_no_certificada(self):
        resultado = despacho_simulado(
            "¿Cuántos Documentos no tienen "
            "status igual a ACTIVO?",
            self.plan,
            Mock(return_value=True),
            self.ejecutor,
        )

        self.assertFalse(resultado["ok"])
        self.ejecutor.assert_not_called()

    def test_05_autorizador_no_puede_mutar_plan(self):
        def alterar_plan(plan):
            plan["filtros"][0]["valor"] = "CERRADO"
            return True

        resultado = despacho_simulado(
            PREGUNTA,
            self.plan,
            alterar_plan,
            self.ejecutor,
        )

        # Se entrega una copia al autorizador.
        # La alteracion no modifica el plan protegido.
        self.assertTrue(resultado["ok"])
        self.assertEqual(
            self.ejecutor.call_args.args[0]
            ["filtros"][0]["valor"],
            "ACTIVO",
        )

    def test_06_autorizador_con_excepcion(self):
        autorizador = Mock(
            side_effect=RuntimeError("fallo de autorizacion")
        )

        resultado = despacho_simulado(
            PREGUNTA,
            self.plan,
            autorizador,
            self.ejecutor,
        )

        self.assertFalse(resultado["ok"])
        self.ejecutor.assert_not_called()

    def test_07_certificado_externo_no_es_permiso(self):
        plan = deepcopy(self.plan)
        plan["certificacion_limitada"] = True

        resultado = despacho_simulado(
            PREGUNTA,
            plan,
            Mock(return_value=True),
            self.ejecutor,
        )

        self.assertFalse(resultado["ok"])
        self.ejecutor.assert_not_called()
