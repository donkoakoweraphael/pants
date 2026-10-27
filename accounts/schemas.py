from typing import List, Optional
from ninja import Schema
from pydantic import Field, field_validator
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from core.schemas import AuditOut
from accounts.models import StatutUtilisateur


# =============================================================================
# SCHÉMAS : AUTHENTIFICATION & MOT DE PASSE
# =============================================================================

class ConnexionIn(Schema):
    """Payload de connexion utilisateur."""
    courriel: str = Field(..., description="Adresse courriel", example="admin@pants.tg")
    password: str = Field(..., description="Mot de passe", example="motdepassefort123")


class TokenOut(Schema):
    """Réponse d'authentification contenant le jeton Bearer JWT."""
    access_token: str
    token_type: str = "bearer"
    doit_changer_mot_de_passe: bool
    utilisateur_id: int
    courriel: str


class ChangementMotDePasseIn(Schema):
    """Payload pour le changement obligatoire ou volontaire de mot de passe."""
    ancien_mot_de_passe: str = Field(..., description="Mot de passe actuel ou temporaire")
    nouveau_mot_de_passe: str = Field(..., min_length=8, description="Nouveau mot de passe (min 8 caractères)")
    confirmation_mot_de_passe: str = Field(..., min_length=8, description="Confirmation identique")


class ReinitialisationMotDePasseOut(Schema):
    """Réponse suite à la réinitialisation d'un mot de passe par un administrateur."""
    message: str
    utilisateur_id: int
    mot_de_passe_temporaire: str


# =============================================================================
# SCHÉMAS : PERMISSIONS (Lecture seule)
# =============================================================================

class PermissionOut(AuditOut):
    """Représentation publique d'une permission."""
    code: str
    libelle: str


# =============================================================================
# SCHÉMAS : RÔLES (RBAC)
# =============================================================================

class RoleCreateIn(Schema):
    """Payload de création d'un rôle."""
    libelle: str = Field(..., min_length=2, max_length=100, example="Enquêteur")
    permission_ids: List[int] = Field(default_factory=list, description="IDs des permissions associées")


class RoleUpdateIn(Schema):
    """Payload de remplacement complet d'un rôle."""
    libelle: str = Field(..., min_length=2, max_length=100, example="Superviseur")
    permission_ids: List[int] = Field(default_factory=list, description="IDs des permissions associées")


class RolePatchIn(Schema):
    """Payload de modification partielle d'un rôle."""
    libelle: Optional[str] = Field(None, min_length=2, max_length=100)
    permission_ids: Optional[List[int]] = None


class RoleOut(AuditOut):
    """Représentation simplifiée d'un rôle pour les listes."""
    libelle: str
    permissions_count: int


class RoleDetailOut(AuditOut):
    """Représentation détaillée d'un rôle avec liste complète des permissions."""
    libelle: str
    permissions: List[PermissionOut]


# =============================================================================
# SCHÉMAS : UTILISATEURS
# =============================================================================

class UtilisateurCreateIn(Schema):
    """
    Payload de création d'un utilisateur par l'administrateur.
    Le mot de passe n'est pas fourni : le système le génère automatiquement.
    """
    courriel: str = Field(..., example="jean.dupont@pants.tg")
    nom: str = Field(..., min_length=1, max_length=150, example="Dupont")
    prenom: str = Field(..., min_length=1, max_length=150, example="Jean")
    tel: Optional[str] = Field("", max_length=30, example="+22890000000")
    statut: StatutUtilisateur = Field(StatutUtilisateur.ACTIF, example=StatutUtilisateur.ACTIF)
    role_id: Optional[int] = Field(None, description="ID du rôle métier")
    permission_ids: List[int] = Field(default_factory=list, description="IDs des permissions directes")

    @field_validator("courriel")
    @classmethod
    def valider_format_courriel(cls, v: str) -> str:
        v = v.lower().strip()
        try:
            validate_email(v)
        except DjangoValidationError:
            raise ValueError("Adresse courriel invalide.")
        return v


class UtilisateurCreatedOut(AuditOut):
    """
    Réponse renvoyée UNE SEULE FOIS lors de la création d'un utilisateur,
    contenant le mot de passe temporaire en clair à transmettre à l'intéressé.
    """
    courriel: str
    nom: str
    prenom: str
    tel: str
    statut: str
    is_active: bool
    doit_changer_mot_de_passe: bool
    mot_de_passe_temporaire: str
    role_id: Optional[int] = None


class UtilisateurUpdateIn(Schema):
    """Payload de remplacement complet des données métier d'un utilisateur."""
    nom: str = Field(..., min_length=1, max_length=150)
    prenom: str = Field(..., min_length=1, max_length=150)
    tel: Optional[str] = Field("", max_length=30)
    statut: StatutUtilisateur = StatutUtilisateur.ACTIF
    role_id: Optional[int] = None
    permission_ids: List[int] = Field(default_factory=list)


class UtilisateurPatchIn(Schema):
    """Payload de mise à jour partielle d'un utilisateur."""
    nom: Optional[str] = Field(None, min_length=1, max_length=150)
    prenom: Optional[str] = Field(None, min_length=1, max_length=150)
    tel: Optional[str] = None
    statut: Optional[StatutUtilisateur] = None
    role_id: Optional[int] = None
    permission_ids: Optional[List[int]] = None


class UtilisateurOut(AuditOut):
    """Représentation d'un utilisateur pour les listes."""
    courriel: str
    nom: str
    prenom: str
    tel: str
    statut: str
    is_active: bool
    doit_changer_mot_de_passe: bool
    role_id: Optional[int] = None
    role_libelle: Optional[str] = None


class UtilisateurDetailOut(AuditOut):
    """Fiche détaillée complète d'un utilisateur avec ses permissions effectives."""
    courriel: str
    nom: str
    prenom: str
    tel: str
    statut: str
    is_active: bool
    is_staff: bool
    is_superuser: bool
    doit_changer_mot_de_passe: bool
    role: Optional[RoleOut] = None
    permissions: List[PermissionOut] = Field(default_factory=list)
    permissions_effectives: List[str] = Field(default_factory=list)
