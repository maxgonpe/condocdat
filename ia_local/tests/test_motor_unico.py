"""Contrato único: consola y HTTP no interpretan ni ejecutan por separado."""
import json
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from io import StringIO

PREGUNTA = "¿Cuántos documentos tenemos registrados?"
OK = {"ok": True, "ejecutado": True, "estado": "respuesta_formateada",
      "pregunta": PREGUNTA, "respuesta": "Tenemos 888 documentos.",
      "modelo": "documents.Document", "total": 888,
      "diagnostico": {"circuito": "Qwen-tools", "tool_calls": []}}
NO = {"ok": False, "ejecutado": False, "estado": "entidad_no_admitida",
      "pregunta": PREGUNTA, "respuesta": "Entidad no admitida",
      "diagnostico": {"circuito": "Qwen-tools", "tool_calls": []}}

class ContratoMotorUnicoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(
            username="motor_unico_test", password="password-test-123", is_staff=True)

    def setUp(self):
        self.client.force_login(self.usuario)

    def test_api_json_delega_una_vez(self):
        with patch("ia_local.services.tool_runtime.resolver_pregunta", return_value=OK) as motor:
            respuesta = self.client.post("/ia/consultar/", {"pregunta": PREGUNTA})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), OK)
        motor.assert_called_once()
        self.assertEqual(motor.call_args.args[1], PREGUNTA)

    def test_contextual_delega_una_vez(self):
        with patch("ia_local.services.tool_runtime.resolver_pregunta", return_value=OK) as motor:
            respuesta = self.client.post("/ia/consultar-contextual/", {"pregunta": PREGUNTA})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), OK)
        motor.assert_called_once()

    def test_diagnostico_delega_una_vez_y_muestra_json(self):
        with patch("ia_local.services.tool_runtime.resolver_pregunta", return_value=OK) as motor:
            respuesta = self.client.post("/ia/diagnostico/", {"pregunta": PREGUNTA})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["resultado_final"], OK)
        self.assertEqual(json.loads(respuesta.context["resultado_json"]), OK)
        motor.assert_called_once()

    def test_rechazo_igual_en_ambos_endpoints(self):
        with patch("ia_local.services.tool_runtime.resolver_pregunta", return_value=NO) as motor:
            a = self.client.post("/ia/consultar/", {"pregunta": PREGUNTA})
            b = self.client.post("/ia/consultar-contextual/", {"pregunta": PREGUNTA})
            d = self.client.post("/ia/diagnostico/", {"pregunta": PREGUNTA})
        self.assertEqual(a.json(), NO)
        self.assertEqual(b.json(), NO)
        self.assertEqual(d.context["resultado_final"], NO)
        self.assertEqual(motor.call_count, 3)

    def test_consola_delega_al_mismo_motor(self):
        salida = StringIO()
        with patch("ia_local.services.tool_runtime.resolver_pregunta", return_value=OK) as motor:
            call_command("ia_preguntar", PREGUNTA, usuario=self.usuario.username, stdout=salida)
        self.assertEqual(json.loads(salida.getvalue()), OK)
        motor.assert_called_once()
        self.assertEqual(motor.call_args.args[1], PREGUNTA)

    def test_usuario_sin_sesion_no_ingresa_a_api(self):
        self.client.logout()
        with patch("ia_local.services.tool_runtime.resolver_pregunta") as motor:
            respuesta = self.client.post("/ia/consultar/", {"pregunta": PREGUNTA})
        self.assertEqual(respuesta.status_code, 302)
        motor.assert_not_called()
