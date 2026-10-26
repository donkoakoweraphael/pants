from datetime import datetime
from typing import Optional, Any
from ninja import Schema
from pydantic import Field


class ErrorResponse(Schema):
    """Schéma standardisé de réponse d'erreur pour l'API."""

    message: str = Field(..., description="Message explicatif de l'erreur lisible par l'utilisateur", example="Ressource introuvable.")
    code: str = Field("ERROR", description="Code technique de l'erreur", example="NOT_FOUND")
    details: Optional[Any] = Field(None, description="Détails contextuels ou erreurs de champs")


class SuccessResponse(Schema):
    """Schéma générique pour confirmer une action effectuée avec succès."""

    success: bool = Field(True, description="Indicateur de succès")
    message: str = Field("Opération effectuée avec succès.", description="Message de confirmation")


class AuditOut(Schema):
    """Schéma réutilisable représentant les champs d'audit de MyBaseModel en snake_case."""

    id: int
    date_creation: datetime
    date_modification: datetime
    cree_par_id: Optional[int] = None
    modifie_par_id: Optional[int] = None
