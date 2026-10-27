import logging
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from accounts.models import Permission
from accounts.constants import CodePermission

logger = logging.getLogger(__name__)


@receiver(post_migrate)
def synchroniser_permissions(sender, **kwargs):
    """
    Synchronise automatiquement le catalogue des permissions en base de données
    à chaque migration de l'application accounts.
    """
    if sender.name == "accounts":
        crees = 0
        mis_a_jour = 0
        for code, libelle in CodePermission.choices:
            _, created = Permission.objects.update_or_create(
                code=code,
                defaults={"libelle": libelle},
            )
            if created:
                crees += 1
            else:
                mis_a_jour += 1
        logger.info(
            f"[post_migrate:accounts] Permissions synchronisées : {crees} créées, {mis_a_jour} vérifiées."
        )
