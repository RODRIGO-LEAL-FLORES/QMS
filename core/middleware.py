from django.contrib import messages
from django.db.utils import DataError, IntegrityError
from django.shortcuts import redirect

from .user_messages import mensaje_error_guardado


class MensajesErroresBaseDatosMiddleware:
    """Evita mostrar errores técnicos de la base de datos al usuario."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not isinstance(exception, (DataError, IntegrityError)):
            return None

        messages.error(request, mensaje_error_guardado(exception))
        destino = request.META.get('HTTP_REFERER') or request.path
        return redirect(destino)