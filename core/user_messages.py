import re

from django.core.exceptions import ValidationError
from django.db.utils import DataError, IntegrityError


def mensaje_error_guardado(error, campo=None, limite=None):
    """Convierte errores técnicos de guardado en mensajes comprensibles."""
    if isinstance(error, DataError) or 'character varying' in str(error).lower():
        if campo and limite:
            return (
                f'El campo "{campo}" supera el máximo de {limite} caracteres. '
                'Acorta el texto e inténtalo nuevamente.'
            )

        match = re.search(r'character varying\((\d+)\)', str(error), re.IGNORECASE)
        if match:
            return (
                f'El texto ingresado supera el máximo de {match.group(1)} caracteres. '
                'Acórtalo e inténtalo nuevamente.'
            )

        return (
            'Uno de los textos ingresados supera el límite permitido. '
            'Acórtalo e inténtalo nuevamente.'
        )

    if isinstance(error, IntegrityError):
        return 'No se pudo guardar porque el registro ya existe o tiene información relacionada.'

    if isinstance(error, ValidationError):
        return 'Revisa los datos ingresados y corrige los campos marcados.'

    return 'No se pudo completar la operación. Revisa los datos e inténtalo nuevamente.'