from django.db.models import ProtectedError, RestrictedError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler, set_rollback


def manejador_excepciones(exc, context):
    """Etapa 1 (auditoría M3): un borrado que choca con una FK PROTECT o
    RESTRICT ya no termina en error 500. Django revisa esas relaciones
    ANTES de borrar nada, así que al llegar acá no hubo ningún cambio
    parcial: solo se informa por qué no se puede eliminar."""
    if isinstance(exc, (ProtectedError, RestrictedError)):
        # Etapa 4: con ATOMIC_REQUESTS, igual que hace el manejador de DRF
        # para sus propias excepciones, se revierte la petición.
        set_rollback()
        return Response(
            {
                'detail': (
                    'No se puede eliminar este registro porque tiene información '
                    'relacionada que debe conservarse.'
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    return exception_handler(exc, context)
