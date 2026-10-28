from typing import List, Optional
from django.db import transaction
from django.db.models import Q
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext as _
from ninja import Router

from core.schemas import ApiResponse
from core.exceptions import (
    BaseAPIException,
    NotFoundException,
    ConflictException,
    UnauthorizedException,
    PermissionDeniedException,
)
from accounts.models import StatutUtilisateur, Permission, Role, Utilisateur
from accounts.constants import CodePermission
from accounts.security import (
    jwt_auth,
    require_permission,
    creer_access_token,
    generer_mot_de_passe_temporaire,
)
from accounts.schemas import (
    ConnexionIn,
    TokenOut,
    ChangementMotDePasseIn,
    ReinitialisationMotDePasseOut,
    PermissionOut,
    RoleCreateIn,
    RoleUpdateIn,
    RolePatchIn,
    RoleOut,
    RoleDetailOut,
    UtilisateurCreateIn,
    UtilisateurCreatedOut,
    UtilisateurUpdateIn,
    UtilisateurPatchIn,
    UtilisateurOut,
    UtilisateurDetailOut,
)

# Initialisation des 4 routeurs modulaires
router_auth = Router()
router_permissions = Router(auth=jwt_auth)
router_roles = Router(auth=jwt_auth)
router_utilisateurs = Router(auth=jwt_auth)


# =============================================================================
# 1. ROUTEUR : AUTHENTIFICATION (/api/auth)
# =============================================================================

@router_auth.post("/connexion", response=ApiResponse[TokenOut], summary="Connexion utilisateur")
def connexion(request, payload: ConnexionIn):
    """
    Authentifie l'utilisateur via son courriel et son mot de passe,
    puis renvoie le jeton d'accès JWT ainsi que l'état de quarantaine (doit_changer_mot_de_passe).
    """
    user = authenticate(username=payload.courriel, password=payload.password)

    if not user:
        raise UnauthorizedException(_("Identifiants invalides (courriel ou mot de passe incorrect)."))

    if not user.is_active:
        raise PermissionDeniedException(_("Votre compte est désactivé ou suspendu. Veuillez contacter un administrateur."))

    token = creer_access_token(user)

    data = TokenOut(
        access_token=token,
        token_type="bearer",
        doit_changer_mot_de_passe=user.doit_changer_mot_de_passe,
        utilisateur_id=user.id,
        courriel=user.courriel,
    )
    return ApiResponse(
        success=True,
        message=_("Connexion réussie."),
        data=data,
    )


# =============================================================================
# 2. ROUTEUR : PERMISSIONS (Lecture seule) (/api/permissions)
# =============================================================================

@router_permissions.get("/", response=ApiResponse[List[PermissionOut]], summary="Lister les permissions")
@require_permission(CodePermission.PERMISSION_VOIR)
def lister_permissions(request, search: Optional[str] = None):
    """Retourne la liste complète du catalogue de permissions."""
    qs = Permission.objects.all().order_by("code")
    if search:
        qs = qs.filter(Q(code__icontains=search) | Q(libelle__icontains=search))
    return ApiResponse(
        success=True,
        message=_("Liste des permissions récupérée avec succès."),
        data=list(qs),
    )


@router_permissions.get("/{int:permission_id}", response=ApiResponse[PermissionOut], summary="Détail d'une permission")
@require_permission(CodePermission.PERMISSION_VOIR)
def detail_permission(request, permission_id: int):
    """Consulte une permission par son identifiant."""
    permission = Permission.objects.filter(id=permission_id).first()
    if not permission:
        raise NotFoundException(f"{_('Permission')} #{permission_id} {_('introuvable.')}")
    return ApiResponse(
        success=True,
        message=_("Détail de la permission récupéré avec succès."),
        data=permission,
    )
# =============================================================================
# 3. ROUTEUR : RÔLES (RBAC) (/api/roles)
# =============================================================================

@router_roles.get("/", response=ApiResponse[List[RoleOut]], summary="Lister les rôles")
@require_permission(CodePermission.ROLE_VOIR)
def lister_roles(request, search: Optional[str] = None):
    """Liste tous les rôles avec le décompte de leurs permissions associées."""
    qs = Role.objects.all().prefetch_related("permissions").order_by("libelle")
    if search:
        qs = qs.filter(libelle__icontains=search)

    resultats = []
    for role in qs:
        data = {
            "id": role.id,
            "libelle": role.libelle,
            "permissions_count": role.permissions.count(),
            "cree_par_id": role.cree_par_id,
            "modifie_par_id": role.modifie_par_id,
            "date_creation": role.date_creation,
            "date_modification": role.date_modification,
        }
        resultats.append(data)
    return ApiResponse(
        success=True,
        message=_("Liste des rôles récupérée avec succès."),
        data=resultats,
    )


@router_roles.post("/", response={201: ApiResponse[RoleDetailOut]}, summary="Créer un rôle")
@require_permission(CodePermission.ROLE_CREER)
def creer_role(request, payload: RoleCreateIn):
    """Crée un rôle et lui associe une liste de permissions."""
    libelle_normalise = payload.libelle.strip()

    if Role.objects.filter(libelle__iexact=libelle_normalise).exists():
        raise ConflictException(f"{_('Un rôle nommé')} '{libelle_normalise}' {_('existe déjà.')}")

    with transaction.atomic():
        role = Role.objects.create(libelle=libelle_normalise)
        if payload.permission_ids:
            perms = list(Permission.objects.filter(id__in=payload.permission_ids))
            if len(perms) != len(set(payload.permission_ids)):
                raise BaseAPIException(_("Une ou plusieurs permissions spécifiées sont inexistantes."))
            role.permissions.set(perms)

    return 201, ApiResponse(
        success=True,
        message=_("Rôle créé avec succès."),
        data=role,
    )


@router_roles.get("/{int:role_id}", response=ApiResponse[RoleDetailOut], summary="Détail d'un rôle")
@require_permission(CodePermission.ROLE_VOIR)
def detail_role(request, role_id: int):
    """Consulte un rôle et la liste complète de ses permissions."""
    role = Role.objects.prefetch_related("permissions").filter(id=role_id).first()
    if not role:
        raise NotFoundException(f"{_('Rôle')} #{role_id} {_('introuvable.')}")
    return ApiResponse(
        success=True,
        message=_("Détail du rôle récupéré avec succès."),
        data=role,
    )


@router_roles.put("/{int:role_id}", response=ApiResponse[RoleDetailOut], summary="Remplacer un rôle")
@require_permission(CodePermission.ROLE_MODIFIER)
def modifier_role(request, role_id: int, payload: RoleUpdateIn):
    """Remplace complètement les attributs et permissions d'un rôle."""
    role = Role.objects.filter(id=role_id).first()
    if not role:
        raise NotFoundException(f"{_('Rôle')} #{role_id} {_('introuvable.')}")

    libelle_normalise = payload.libelle.strip()
    if Role.objects.filter(libelle__iexact=libelle_normalise).exclude(id=role.id).exists():
        raise ConflictException(f"{_('Un autre rôle nommé')} '{libelle_normalise}' {_('existe déjà.')}")

    with transaction.atomic():
        role.libelle = libelle_normalise
        role.save()
        perms = list(Permission.objects.filter(id__in=payload.permission_ids))
        if len(perms) != len(set(payload.permission_ids)):
            raise BaseAPIException(_("Une ou plusieurs permissions spécifiées sont inexistantes."))
        role.permissions.set(perms)

    return ApiResponse(
        success=True,
        message=_("Rôle modifié avec succès."),
        data=role,
    )


@router_roles.patch("/{int:role_id}", response=ApiResponse[RoleDetailOut], summary="Modifier partiellement un rôle")
@require_permission(CodePermission.ROLE_MODIFIER)
def patch_role(request, role_id: int, payload: RolePatchIn):
    """Met à jour partiellement le libellé ou les permissions d'un rôle."""
    role = Role.objects.filter(id=role_id).first()
    if not role:
        raise NotFoundException(f"{_('Rôle')} #{role_id} {_('introuvable.')}")

    with transaction.atomic():
        if payload.libelle is not None:
            libelle_normalise = payload.libelle.strip()
            if Role.objects.filter(libelle__iexact=libelle_normalise).exclude(id=role.id).exists():
                raise ConflictException(f"{_('Un autre rôle nommé')} '{libelle_normalise}' {_('existe déjà.')}")
            role.libelle = libelle_normalise
            role.save()

        if payload.permission_ids is not None:
            perms = list(Permission.objects.filter(id__in=payload.permission_ids))
            if len(perms) != len(set(payload.permission_ids)):
                raise BaseAPIException(_("Une ou plusieurs permissions spécifiées sont inexistantes."))
            role.permissions.set(perms)

    return ApiResponse(
        success=True,
        message=_("Rôle mis à jour avec succès."),
        data=role,
    )


@router_roles.delete("/{int:role_id}", response=ApiResponse[None], summary="Supprimer un rôle")
@require_permission(CodePermission.ROLE_SUPPRIMER)
def supprimer_role(request, role_id: int):
    """
    Supprime un rôle à condition qu'aucun utilisateur n'y soit rattaché.
    Protection d'intégrité référentielle stricte.
    """
    role = Role.objects.filter(id=role_id).first()
    if not role:
        raise NotFoundException(f"{_('Rôle')} #{role_id} {_('introuvable.')}")

    nb_utilisateurs = role.utilisateurs.count()
    if nb_utilisateurs > 0:
        raise ConflictException(
            f"{_('Impossible de supprimer le rôle')} '{role.libelle}' {_('car il est actuellement attribué à')} {nb_utilisateurs} {_('utilisateur(s).')}"
        )

    role.delete()
    return ApiResponse(
        success=True,
        message=f"{_('Le rôle')} '{role.libelle}' {_('a été supprimé avec succès.')}",
    )


# =============================================================================
# 4. ROUTEUR : UTILISATEURS (/api/utilisateurs)
# =============================================================================

def formater_utilisateur_detail(user: Utilisateur) -> dict:
    """Helper pour construire la vue détaillée complète avec permissions effectives."""
    role_data = None
    if user.role:
        role_data = {
            "id": user.role.id,
            "libelle": user.role.libelle,
            "permissions_count": user.role.permissions.count(),
            "cree_par_id": user.role.cree_par_id,
            "modifie_par_id": user.role.modifie_par_id,
            "date_creation": user.role.date_creation,
            "date_modification": user.role.date_modification,
        }

    return {
        "id": user.id,
        "courriel": user.courriel,
        "nom": user.nom,
        "prenom": user.prenom,
        "tel": user.tel,
        "statut": user.statut,
        "is_active": user.is_active,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "doit_changer_mot_de_passe": user.doit_changer_mot_de_passe,
        "role": role_data,
        "permissions": list(user.permissions.all()),
        "permissions_effectives": sorted(list(user.get_all_permissions_codes())),
        "cree_par_id": user.cree_par_id,
        "modifie_par_id": user.modifie_par_id,
        "date_creation": user.date_creation,
        "date_modification": user.date_modification,
    }


@router_utilisateurs.get("/", response=ApiResponse[List[UtilisateurOut]], summary="Lister les utilisateurs")
@require_permission(CodePermission.UTILISATEUR_VOIR)
def lister_utilisateurs(
    request,
    search: Optional[str] = None,
    statut: Optional[StatutUtilisateur] = None,
    role_id: Optional[int] = None,
):
    """Liste tous les utilisateurs avec filtres métier (statut, rôle, recherche textuelle)."""
    qs = Utilisateur.objects.select_related("role").order_by("nom", "prenom")

    if statut:
        qs = qs.filter(statut=statut)
    if role_id:
        qs = qs.filter(role_id=role_id)
    if search:
        qs = qs.filter(
            Q(courriel__icontains=search)
            | Q(nom__icontains=search)
            | Q(prenom__icontains=search)
            | Q(tel__icontains=search)
        )

    resultats = []
    for u in qs:
        resultats.append({
            "id": u.id,
            "courriel": u.courriel,
            "nom": u.nom,
            "prenom": u.prenom,
            "tel": u.tel,
            "statut": u.statut,
            "is_active": u.is_active,
            "doit_changer_mot_de_passe": u.doit_changer_mot_de_passe,
            "role_id": u.role_id,
            "role_libelle": u.role.libelle if u.role else None,
            "cree_par_id": u.cree_par_id,
            "modifie_par_id": u.modifie_par_id,
            "date_creation": u.date_creation,
            "date_modification": u.date_modification,
        })
    return ApiResponse(
        success=True,
        message=_("Liste des utilisateurs récupérée avec succès."),
        data=resultats,
    )


@router_utilisateurs.post("/", response={201: ApiResponse[UtilisateurCreatedOut]}, summary="Créer un utilisateur (Admin)")
@require_permission(CodePermission.UTILISATEUR_CREER)
def creer_utilisateur(request, payload: UtilisateurCreateIn):
    """
    Crée un nouvel utilisateur.
    L'administrateur ne saisit pas de mot de passe : le système génère un mot de passe
    temporaire sécurisé renvoyé une seule fois dans la réponse.
    """
    courriel_normalise = payload.courriel.lower().strip()

    if Utilisateur.objects.filter(courriel=courriel_normalise).exists():
        raise ConflictException(_("Un utilisateur avec l'adresse '{courriel}' existe déjà.").format(courriel=courriel_normalise))

    role = None
    if payload.role_id:
        role = Role.objects.filter(id=payload.role_id).first()
        if not role:
            raise NotFoundException(f"{_('Rôle')} #{payload.role_id} {_('introuvable.')}")

    mdp_temporaire = generer_mot_de_passe_temporaire(12)

    with transaction.atomic():
        user = Utilisateur(
            courriel=courriel_normalise,
            nom=payload.nom.strip(),
            prenom=payload.prenom.strip(),
            tel=payload.tel.strip() if payload.tel else "",
            statut=payload.statut,
            role=role,
            doit_changer_mot_de_passe=True,
        )
        user.set_password(mdp_temporaire)
        user.save()

        if payload.permission_ids:
            perms = list(Permission.objects.filter(id__in=payload.permission_ids))
            if len(perms) != len(set(payload.permission_ids)):
                raise BaseAPIException(_("Une ou plusieurs permissions spécifiées sont inexistantes."))
            user.permissions.set(perms)

    data = {
        "id": user.id,
        "courriel": user.courriel,
        "nom": user.nom,
        "prenom": user.prenom,
        "tel": user.tel,
        "statut": user.statut,
        "is_active": user.is_active,
        "doit_changer_mot_de_passe": user.doit_changer_mot_de_passe,
        "mot_de_passe_temporaire": mdp_temporaire,
        "role_id": user.role_id,
        "cree_par_id": user.cree_par_id,
        "modifie_par_id": user.modifie_par_id,
        "date_creation": user.date_creation,
        "date_modification": user.date_modification,
    }
    return 201, ApiResponse(
        success=True,
        message=_("Utilisateur créé avec succès."),
        data=data,
    )


@router_utilisateurs.get("/me", response=ApiResponse[UtilisateurDetailOut], summary="Consulter son propre profil")
def profil_connecte(request):
    """
    Retourne la fiche détaillée de l'utilisateur connecté.
    Accessible en permanence, y compris en quarantaine pour vérifier doit_changer_mot_de_passe.
    """
    user = Utilisateur.objects.select_related("role").prefetch_related("permissions", "role__permissions").get(id=request.user.id)
    return ApiResponse(
        success=True,
        message=_("Profil récupéré avec succès."),
        data=formater_utilisateur_detail(user),
    )


@router_utilisateurs.post("/me/changer-mot-de-passe", response=ApiResponse[None], summary="Changer son mot de passe")
def changer_mot_de_passe_connecte(request, payload: ChangementMotDePasseIn):
    """
    Permet à l'utilisateur connecté de modifier son mot de passe.
    Obligatoire à la première connexion pour lever la quarantaine (doit_changer_mot_de_passe -> False).
    """
    user = request.user

    # 1. Vérification de l'ancien mot de passe
    if not user.check_password(payload.ancien_mot_de_passe):
        raise BaseAPIException(_("L'ancien mot de passe fourni est incorrect."), code="INVALID_OLD_PASSWORD")

    # 2. Vérification de la confirmation
    if payload.nouveau_mot_de_passe != payload.confirmation_mot_de_passe:
        raise BaseAPIException(_("Le nouveau mot de passe et sa confirmation ne correspondent pas."), code="PASSWORD_MISMATCH")

    # 3. Interdiction de réutiliser le même mot de passe
    if payload.ancien_mot_de_passe == payload.nouveau_mot_de_passe:
        raise BaseAPIException(_("Le nouveau mot de passe doit être différent de l'ancien."), code="SAME_PASSWORD")

    # 4. Validation des règles de complexité Django
    try:
        validate_password(payload.nouveau_mot_de_passe, user=user)
    except DjangoValidationError as exc:
        raise BaseAPIException(_("Mot de passe trop simple."), details=list(exc.messages), code="WEAK_PASSWORD")

    # 5. Enregistrement et levée de la quarantaine
    user.set_password(payload.nouveau_mot_de_passe)
    user.doit_changer_mot_de_passe = False
    user.save(update_fields=["password", "doit_changer_mot_de_passe"])

    return ApiResponse(
        success=True,
        message=_("Votre mot de passe a été modifié avec succès. Votre accès est désormais actif."),
    )


@router_utilisateurs.get("/{int:utilisateur_id}", response=ApiResponse[UtilisateurDetailOut], summary="Détail d'un utilisateur")
@require_permission(CodePermission.UTILISATEUR_VOIR)
def detail_utilisateur(request, utilisateur_id: int):
    """Consulte la fiche complète d'un utilisateur et ses permissions effectives."""
    user = Utilisateur.objects.select_related("role").prefetch_related("permissions", "role__permissions").filter(id=utilisateur_id).first()
    if not user:
        raise NotFoundException(f"{_('Utilisateur')} #{utilisateur_id} {_('introuvable.')}")
    return ApiResponse(
        success=True,
        message=_("Fiche utilisateur récupérée avec succès."),
        data=formater_utilisateur_detail(user),
    )


@router_utilisateurs.put("/{int:utilisateur_id}", response=ApiResponse[UtilisateurDetailOut], summary="Remplacer un utilisateur")
@require_permission(CodePermission.UTILISATEUR_MODIFIER)
def modifier_utilisateur(request, utilisateur_id: int, payload: UtilisateurUpdateIn):
    """Remplacement complet des informations métier d'un utilisateur."""
    user = Utilisateur.objects.filter(id=utilisateur_id).first()
    if not user:
        raise NotFoundException(f"{_('Utilisateur')} #{utilisateur_id} {_('introuvable.')}")

    role = None
    if payload.role_id:
        role = Role.objects.filter(id=payload.role_id).first()
        if not role:
            raise NotFoundException(f"{_('Rôle')} #{payload.role_id} {_('introuvable.')}")

    with transaction.atomic():
        user.nom = payload.nom.strip()
        user.prenom = payload.prenom.strip()
        user.tel = payload.tel.strip() if payload.tel else ""
        user.statut = payload.statut
        user.role = role
        user.save()

        perms = list(Permission.objects.filter(id__in=payload.permission_ids))
        if len(perms) != len(set(payload.permission_ids)):
            raise BaseAPIException(_("Une ou plusieurs permissions spécifiées sont inexistantes."))
        user.permissions.set(perms)

    user = Utilisateur.objects.select_related("role").prefetch_related("permissions", "role__permissions").get(id=user.id)
    return ApiResponse(
        success=True,
        message=_("Utilisateur remplacé avec succès."),
        data=formater_utilisateur_detail(user),
    )


@router_utilisateurs.patch("/{int:utilisateur_id}", response=ApiResponse[UtilisateurDetailOut], summary="Modifier partiellement un utilisateur")
@require_permission(CodePermission.UTILISATEUR_MODIFIER)
def patch_utilisateur(request, utilisateur_id: int, payload: UtilisateurPatchIn):
    """Mise à jour partielle des champs d'un utilisateur."""
    user = Utilisateur.objects.filter(id=utilisateur_id).first()
    if not user:
        raise NotFoundException(f"{_('Utilisateur')} #{utilisateur_id} {_('introuvable.')}")

    with transaction.atomic():
        if payload.nom is not None:
            user.nom = payload.nom.strip()
        if payload.prenom is not None:
            user.prenom = payload.prenom.strip()
        if payload.tel is not None:
            user.tel = payload.tel.strip()
        if payload.statut is not None:
            user.statut = payload.statut
        if payload.role_id is not None:
            if payload.role_id == 0:
                user.role = None
            else:
                role = Role.objects.filter(id=payload.role_id).first()
                if not role:
                    raise NotFoundException(f"{_('Rôle')} #{payload.role_id} {_('introuvable.')}")
                user.role = role

        user.save()

        if payload.permission_ids is not None:
            perms = list(Permission.objects.filter(id__in=payload.permission_ids))
            if len(perms) != len(set(payload.permission_ids)):
                raise BaseAPIException(_("Une ou plusieurs permissions spécifiées sont inexistantes."))
            user.permissions.set(perms)

    user = Utilisateur.objects.select_related("role").prefetch_related("permissions", "role__permissions").get(id=user.id)
    return ApiResponse(
        success=True,
        message=_("Utilisateur mis à jour avec succès."),
        data=formater_utilisateur_detail(user),
    )


@router_utilisateurs.post("/{int:utilisateur_id}/desactiver", response=ApiResponse[None], summary="Désactiver un utilisateur")
@require_permission(CodePermission.UTILISATEUR_DESACTIVER)
def desactiver_utilisateur(request, utilisateur_id: int):
    """Désactive un compte utilisateur en basculant son statut à DESACTIVE."""
    user = Utilisateur.objects.filter(id=utilisateur_id).first()
    if not user:
        raise NotFoundException(f"{_('Utilisateur')} #{utilisateur_id} {_('introuvable.')}")

    user.statut = StatutUtilisateur.DESACTIVE
    user.save(update_fields=["statut"])

    return ApiResponse(
        success=True,
        message=_("L'utilisateur '{courriel}' a été désactivé avec succès.").format(courriel=user.courriel),
    )


@router_utilisateurs.post("/{int:utilisateur_id}/suspendre", response=ApiResponse[None], summary="Suspendre un utilisateur")
@require_permission(CodePermission.UTILISATEUR_SUSPENDRE)
def suspendre_utilisateur(request, utilisateur_id: int):
    """Suspend temporairement un compte utilisateur en basculant son statut à SUSPENDU."""
    user = Utilisateur.objects.filter(id=utilisateur_id).first()
    if not user:
        raise NotFoundException(f"{_('Utilisateur')} #{utilisateur_id} {_('introuvable.')}")

    user.statut = StatutUtilisateur.SUSPENDU
    user.save(update_fields=["statut"])

    return ApiResponse(
        success=True,
        message=_("Le compte '{courriel}' a été suspendu avec succès.").format(courriel=user.courriel),
    )


@router_utilisateurs.post("/{int:utilisateur_id}/reactiver", response=ApiResponse[None], summary="Réactiver un utilisateur")
@require_permission(CodePermission.UTILISATEUR_REACTIVER)
def reactiver_utilisateur(request, utilisateur_id: int):
    """Réactive un compte désactivé ou suspendu en basculant son statut à ACTIF."""
    user = Utilisateur.objects.filter(id=utilisateur_id).first()
    if not user:
        raise NotFoundException(f"{_('Utilisateur')} #{utilisateur_id} {_('introuvable.')}")

    user.statut = StatutUtilisateur.ACTIF
    user.save(update_fields=["statut"])

    return ApiResponse(
        success=True,
        message=_("Le compte '{courriel}' a été réactivé avec succès.").format(courriel=user.courriel),
    )


@router_utilisateurs.post("/{int:utilisateur_id}/reinitialiser-mot-de-passe", response=ApiResponse[ReinitialisationMotDePasseOut], summary="Réinitialiser le mot de passe (Admin)")
@require_permission(CodePermission.UTILISATEUR_REINITIALISER_MDP)
def reinitialiser_mot_de_passe(request, utilisateur_id: int):
    """
    Réinitialise le mot de passe d'un utilisateur par l'administrateur.
    Génère un nouveau mot de passe temporaire et remet le compte en quarantaine (doit_changer_mot_de_passe = True).
    """
    user = Utilisateur.objects.filter(id=utilisateur_id).first()
    if not user:
        raise NotFoundException(f"{_('Utilisateur')} #{utilisateur_id} {_('introuvable.')}")

    nouveau_mdp_temp = generer_mot_de_passe_temporaire(12)
    user.set_password(nouveau_mdp_temp)
    user.doit_changer_mot_de_passe = True
    user.save(update_fields=["password", "doit_changer_mot_de_passe"])

    data = ReinitialisationMotDePasseOut(
        message=f"Le mot de passe de l'utilisateur '{user.courriel}' a été réinitialisé.",
        utilisateur_id=user.id,
        mot_de_passe_temporaire=nouveau_mdp_temp,
    )
    return ApiResponse(
        success=True,
        message=_("Le mot de passe de l'utilisateur '{courriel}' a été réinitialisé avec succès.").format(courriel=user.courriel),
        data=data,
    )
