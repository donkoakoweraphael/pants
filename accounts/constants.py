from django.db import models


class CodePermission(models.TextChoices):
    """
    Catalogue centralisé de toutes les permissions du système.
    Chaque membre définit le code technique unique et son libellé descriptif.
    Format :
        CODE_TECHNIQUE = "CODE_TECHNIQUE", "Libellé de la permission en français"
    """

    # =========================================================================
    # APPLICATION : ACCOUNTS (Gestion des utilisateurs, des rôles et des accès)
    # =========================================================================
    UTILISATEUR_VOIR = "UTILISATEUR_VOIR", "Consulter la liste et le profil des utilisateurs"
    UTILISATEUR_CREER = "UTILISATEUR_CREER", "Créer un nouvel utilisateur"
    UTILISATEUR_MODIFIER = "UTILISATEUR_MODIFIER", "Modifier les informations d'un utilisateur"
    UTILISATEUR_DESACTIVER = "UTILISATEUR_DESACTIVER", "Désactiver un compte utilisateur"
    UTILISATEUR_SUSPENDRE = "UTILISATEUR_SUSPENDRE", "Suspendre un compte utilisateur"
    UTILISATEUR_REACTIVER = (
        "UTILISATEUR_REACTIVER",
        "Réactiver un compte utilisateur désactivé ou suspendu",
    )
    UTILISATEUR_REINITIALISER_MDP = (
        "UTILISATEUR_REINITIALISER_MDP",
        "Réinitialiser le mot de passe d'un utilisateur",
    )

    ROLE_VOIR = "ROLE_VOIR", "Consulter les rôles et leurs permissions"
    ROLE_CREER = "ROLE_CREER", "Créer un nouveau rôle"
    ROLE_MODIFIER = "ROLE_MODIFIER", "Modifier un rôle existant"
    ROLE_SUPPRIMER = "ROLE_SUPPRIMER", "Supprimer un rôle non assigné"

    PERMISSION_VOIR = "PERMISSION_VOIR", "Consulter le catalogue des permissions"

    # =========================================================================
    # APPLICATION : SITES / ÉTABLISSEMENTS (Exemple pour les futures applications)
    # Déclarer ici les permissions des nouveaux modules métier selon le même format :
    # =========================================================================
    # ETABLISSEMENT_VOIR = "ETABLISSEMENT_VOIR", "Consulter les établissements"
    # ETABLISSEMENT_CREER = "ETABLISSEMENT_CREER", "Créer un nouvel établissement"
