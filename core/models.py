from django.db import models
from django.conf import settings
from core.context import get_current_user


class MyBaseModel(models.Model):
    """
    Modèle de base abstrait fournissant l'audit automatique (traçabilité).
    Tous les modèles du domaine métier héritent de cette classe.
    Conforme aux standards PEP 8 et conventions de nommage Django (snake_case).
    """

    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_crees",
        verbose_name="Créé par",
    )
    modifie_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_modifies",
        verbose_name="Modifié par",
    )
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création",
    )
    date_modification = models.DateTimeField(
        auto_now=True,
        verbose_name="Date de dernière modification",
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """
        Intercepte la sauvegarde pour renseigner automatiquement cree_par et modifie_par
        à partir de l'utilisateur stocké dans le contexte de requête.
        Gère également de façon sécurisée le cas d'une sauvegarde restreinte (update_fields).
        """
        user = get_current_user()
        is_new = not self.pk

        if user and getattr(user, "is_authenticated", False):
            # Si c'est une création (pas de clé primaire et cree_par pas encore valorisé)
            if is_new and not self.cree_par_id:
                self.cree_par = user
            # À chaque modification ou création
            self.modifie_par = user

        # Si l'appelant a restreint les colonnes à sauvegarder via update_fields
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            extra_fields = {"modifie_par", "date_modification"}
            if is_new:
                extra_fields.update({"cree_par", "date_creation"})
            kwargs["update_fields"] = set(update_fields) | extra_fields

        super().save(*args, **kwargs)
