"""Consola del mismo motor que las dos páginas web."""
import json
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.test import RequestFactory
from ia_local.services.tool_runtime import resolver_pregunta

class Command(BaseCommand):
    help = "Pregunta al mismo motor Qwen-tools de la interfaz y el diagnóstico"

    def add_arguments(self, parser):
        parser.add_argument("pregunta")
        parser.add_argument("--usuario", required=True)

    def handle(self, *args, **opts):
        usuario = get_user_model().objects.filter(username=opts["usuario"], is_active=True).first()
        if usuario is None:
            raise CommandError("Usuario inexistente o inactivo")
        request = RequestFactory().post("/ia/consultar/", data={"pregunta": opts["pregunta"]})
        request.user = usuario
        resultado = resolver_pregunta(request, opts["pregunta"])
        self.stdout.write(json.dumps(resultado, ensure_ascii=False, indent=2, default=str))
