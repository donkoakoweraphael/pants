from datetime import datetime
from typing import Optional, Any, Generic, TypeVar
from ninja import Schema
from pydantic import Field

T = TypeVar("T")


class ApiResponse(Schema, Generic[T]):
    """
    Enveloppe standardisée pour toutes les réponses de succès de l'API REST.
    Permet au frontend de disposer d'une structure uniforme et prévisible.
    """

    success: bool = Field(True, description="Indicateur de succès de l'opération")
    message: str = Field(
        "Opération effectuée avec succès.",
        description="Message descriptif ou de confirmation lisible par l'utilisateur",
    )
    data: Optional[T] = Field(None, description="Données utiles retournées par l'endpoint")


class ApiErrorResponse(Schema):
    """
    Enveloppe standardisée pour toutes les réponses d'erreur de l'API REST.
    Permet au frontend d'exploiter un format d'erreur uniforme.
    """

    success: bool = Field(False, description="Indicateur d'échec de l'opération")
    message: str = Field(
        ...,
        description="Message d'erreur explicatif lisible par l'utilisateur",
        example="Ressource introuvable.",
    )
    code: str = Field("ERROR", description="Code technique d'erreur", example="NOT_FOUND")
    details: Optional[Any] = Field(
        None, description="Détails contextuels ou erreurs de validation de champs"
    )


# Alias rétro-compatibles
SuccessResponse = ApiResponse[None]
ErrorResponse = ApiErrorResponse


class AuditOut(Schema):
    """Schéma réutilisable représentant les champs d'audit de MyBaseModel en snake_case."""

    id: int
    date_creation: datetime
    date_modification: datetime
    cree_par_id: Optional[int] = None
    modifie_par_id: Optional[int] = None
