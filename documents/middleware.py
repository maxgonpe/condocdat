from django.utils import timezone

from .models import UserPresence


class UserPresenceMiddleware:
    """
    Guarda `last_seen` para usuarios autenticados.

    "En línea" se define como actividad en los últimos N minutos (ver dashboard).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            user = getattr(request, "user", None)
            if user and user.is_authenticated:
                now = timezone.now()
                # Upsert simple
                UserPresence.objects.update_or_create(
                    user=user,
                    defaults={"last_seen": now},
                )
        except Exception:
            # Nunca romper una request por presencia
            pass
        return response

