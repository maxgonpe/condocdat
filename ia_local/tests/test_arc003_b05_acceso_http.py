from unittest.mock import Mock, patch

from django.test import SimpleTestCase, RequestFactory

from ia_local import (
    views,
    views_bridge,
    views_desambiguacion,
)


class TestARC003B05AccesoHTTP(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def _usuario(self, autenticado, staff, activo=True):
        usuario = Mock()
        usuario.is_authenticated = autenticado
        usuario.is_staff = staff
        usuario.is_active = activo
        return usuario

    def _verificar_rechazo(self, vista, usuario):
        request = self.factory.post(
            "/ia-local/consultar/",
            data={"pregunta": "¿Cuántos Documentos hay?"},
        )
        request.user = usuario

        # La función interna no debe ejecutarse.
        with patch(
            "ia_local.views._ejecutar_consulta_ia",
            side_effect=AssertionError(
                "El motor no debe ejecutarse"
            ),
        ):
            respuesta = vista(request)

        self.assertIn(
            respuesta.status_code,
            (301, 302, 403),
        )

    def test_01_anonimo_vista_principal(self):
        self._verificar_rechazo(
            views.consulta_ia,
            self._usuario(False, False),
        )

    def test_02_no_staff_vista_json(self):
        self._verificar_rechazo(
            views.consulta_ia_json,
            self._usuario(True, False),
        )

    def test_03_no_staff_bridge(self):
        self._verificar_rechazo(
            views_bridge.consulta_bridge_json,
            self._usuario(True, False),
        )

    def test_04_no_staff_contextual(self):
        self._verificar_rechazo(
            views_desambiguacion.consultar_con_aclaracion,
            self._usuario(True, False),
        )
