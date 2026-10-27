import functools
import logging
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from ninja.security import HttpBearer
from core.context import set_current_user
from core.exceptions import (
    UnauthorizedException,
    PermissionDeniedException,
    PasswordChangeRequiredException,
)

logger = logging.getLogger(__name__)

# Liste blanche des endpoints accessibles même quand l'utilisateur est en quarantaine
CHEMINS_AUTORISES_EN_QUARANTAINE = {
    "/api/utilisateurs/me",
    "/api/utilisateurs/me/changer-mot-de-passe",
}


def generer_mot_de_passe_temporaire(longueur: int = 12) -> str:
    """
    Génère un mot de passe temporaire aléatoire et hautement sécurisé
    contenant minuscules, majuscules, chiffres et caractères spéciaux.
    """
    if longueur < 10:
        longueur = 12

    minuscules = string.ascii_lowercase
    majuscules = string.ascii_uppercase
    chiffres = string.digits
    speciaux = "!@#$%^&*-_=+"

    # Garantit la présence d'au moins un caractère de chaque catégorie
    mot_de_passe = [
        secrets.choice(minuscules),
        secrets.choice(majuscules),
        secrets.choice(chiffres),
        secrets.choice(speciaux),
    ]

    alphabet_complet = minuscules + majuscules + chiffres + speciaux
    mot_de_passe += [secrets.choice(alphabet_complet) for _ in range(longueur - 4)]

    # Mélange aléatoire sécurisé
    secrets.SystemRandom().shuffle(mot_de_passe)
    return "".join(mot_de_passe)


def creer_access_token(user: Any, duree_minutes: int = 1440) -> str:
    """
    Crée un jeton JWT d'accès valide avec expiration et identifiants de l'utilisateur.
    """
    maintenant = datetime.now(timezone.utc)
    expiration = maintenant + timedelta(minutes=duree_minutes)

    payload = {
        "sub": str(user.id),
        "user_id": user.id,
        "courriel": user.courriel,
        "doit_changer_mot_de_passe": getattr(user, "doit_changer_mot_de_passe", False),
        "iat": maintenant,
        "exp": expiration,
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decoder_access_token(token: str) -> dict:
    """
    Décode et valide un jeton JWT. Lève UnauthorizedException en cas d'invalidation.
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Le jeton d'accès a expiré. Veuillez vous reconnecter.")
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedException(f"Jeton d'accès invalide : {str(exc)}")


class JWTAuth(HttpBearer):
    """
    Gestionnaire d'authentification Bearer JWT pour Django Ninja.
    Applique automatiquement :
    - La Barrière 1 (Garde-fou Quarantaine) : bloque l'accès si doit_changer_mot_de_passe=True
      hors endpoints autorisés.
    - L'injection dans le contexte thread-safe MyBaseModel (set_current_user).
    """

    def authenticate(self, request, token: str) -> Optional[Any]:
        payload = decoder_access_token(token)
        user_id = payload.get("user_id") or payload.get("sub")

        if not user_id:
            raise UnauthorizedException("Jeton d'accès incomplet ou corrompu.")

        User = get_user_model()
        user = User.objects.filter(id=user_id).first()

        if not user or not user.is_active:
            raise UnauthorizedException("Utilisateur introuvable ou compte inactif.")

        # Injection dans la requête et le contexte d'audit
        request.user = user
        set_current_user(user)

        # Barrière 1 : Vérification de la Quarantaine (changement de mot de passe obligatoire)
        if getattr(user, "doit_changer_mot_de_passe", False):
            chemin_normalise = request.path.rstrip("/")
            chemins_autorises = {c.rstrip("/") for c in CHEMINS_AUTORISES_EN_QUARANTAINE}

            if chemin_normalise not in chemins_autorises:
                raise PasswordChangeRequiredException(
                    "Vous devez obligatoirement modifier votre mot de passe temporaire avant d'accéder aux fonctionnalités de l'API."
                )

        return user


jwt_auth = JWTAuth()


def require_permission(code_permission: str):
    """
    Décorateur centralisé pour contrôler les permissions sur un endpoint Ninja.
    Vérifie que l'utilisateur connecté possède le droit requis ou dispose du statut superutilisateur.
    """

    def decorateur(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = getattr(request, "user", None)

            if not user or not getattr(user, "is_authenticated", False):
                raise UnauthorizedException("Authentification requise pour effectuer cette action.")

            if not user.is_active:
                raise PermissionDeniedException("Votre compte est désactivé.")

            # Un superutilisateur bénéficie de tous les privilèges
            if user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Contrôle RBAC des permissions effectives
            droits = user.get_all_permissions_codes()
            if code_permission not in droits:
                raise PermissionDeniedException(
                    f"Privilège insuffisant. Permission requise : '{code_permission}'."
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorateur
