"""
Prueba SMTP desde la configuración del proyecto.

Uso:
  python manage.py test_correo maxgonpe@gmail.com

Comprueba contraseña, red y autenticación Office 365.
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.mail import EmailMessage


class Command(BaseCommand):
    help = "Envía un correo de prueba al destinatario indicado (usa EMAIL_* del .env)."

    def add_arguments(self, parser):
        parser.add_argument("destinatario", type=str, help="Email destino, ej. maxgonpe@gmail.com")

    def handle(self, *args, **options):
        to = (options["destinatario"] or "").strip().replace(",", ".")
        if "@" not in to:
            raise CommandError("Email inválido (¿escribiste gmail,com en vez de gmail.com?)")

        user = getattr(settings, "EMAIL_HOST_USER", "") or ""
        pw = (getattr(settings, "EMAIL_HOST_PASSWORD", None) or "").strip()
        host = getattr(settings, "EMAIL_HOST", "")
        port = getattr(settings, "EMAIL_PORT", 587)

        self.stdout.write(f"SMTP: {host}:{port}  usuario: {user}  (timeout vía EMAIL_TIMEOUT)")
        if not pw:
            raise CommandError(
                "Falta EMAIL_HOST_PASSWORD en .env (o está vacía). "
                "Office 365: crea una «Contraseña de aplicación» en la cuenta Microsoft."
            )
        host_l = (host or "").lower()
        if ("office365" in host_l or "outlook.office" in host_l) and len(pw) < 16:
            self.stdout.write(
                self.style.WARNING(
                    "La contraseña tiene menos de 16 caracteres. "
                    "Las contraseñas de aplicación de Microsoft suelen ser 16 caracteres; "
                    "revisa que no esté cortada en el .env."
                )
            )

        msg = EmailMessage(
            subject="[Condocdat] Prueba test_correo",
            body="Si lees esto, el SMTP está bien configurado.",
            from_email=settings.DEFAULT_FROM_EMAIL or user,
            to=[to],
        )
        try:
            msg.send(fail_silently=False)
        except Exception as e:
            raise CommandError(f"Envío falló: {type(e).__name__}: {e}") from e

        self.stdout.write(self.style.SUCCESS(f"OK: correo enviado a {to}"))
