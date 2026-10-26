from django.db import models
from django.conf import settings
from core.context import get_current_user


class MyBaseModel(models.Model):
    """
    Modèle de base abstrait fournissant l'audit automatique (traçabilité).
    Tous les modèles du domaine métier héritent de cette classe.
    """

    creePar = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_crees",
        verbose_name="Créé par",
    )
    modifiePar = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_modifies",
        verbose_name="Modifié par",
    )
    dateCreation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création",
    )
    dateModification = models.DateTimeField(
        auto_now=True,
        verbose_name="Date de dernière modification",
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """
        Intercepte la sauvegarde pour renseigner automatiquement creePar et modifiePar
        à partir de l'utilisateur stocké dans le contexte de requête.
        """
        user = get_current_user()

        if user and getattr(user, "is_authenticated", False):
            # Si c'est une création (pas de clé primaire et creePar pas encore valorisé)
            if not self.pk and not self.creePar_id:
                self.creePar = user
            # À chaque modification ou création
            self.modifiePar = user

        # Si l'appelant a restreint les colonnes à sauvegarder via update_fields
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = set(update_fields) | {"modifiePar", "dateModification"}

        super().save(*args, **kwargs)
