from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from core.models import MyBaseModel


class UtilisateurManager(BaseUserManager):
    """Gestionnaire personnalisé pour créer des utilisateurs avec leur courriel comme identifiant."""

    def get_by_natural_key(self, username):
        """Permet l'authentification insensible à la casse."""
        if username:
            username = username.lower().strip()
        return self.get(**{self.model.USERNAME_FIELD: username})

    def create_user(self, courriel=None, password=None, **extra_fields):
        if not courriel:
            courriel = extra_fields.pop("username", None) or extra_fields.pop("email", None)
        if not courriel:
            raise ValueError("Le champ courriel est obligatoire.")
        courriel = self.normalize_email(courriel).lower().strip()
        extra_fields.setdefault("statut", StatutUtilisateur.ACTIF)

        # Synchronise is_active avec le statut métier
        is_active = extra_fields.get("statut") == StatutUtilisateur.ACTIF
        extra_fields.setdefault("is_active", is_active)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        user = self.model(courriel=courriel, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, courriel=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("statut", StatutUtilisateur.ACTIF)
        extra_fields.setdefault("nom", "Admin")
        extra_fields.setdefault("prenom", "Super")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Le superutilisateur doit avoir is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Le superutilisateur doit avoir is_superuser=True.")

        return self.create_user(courriel, password, **extra_fields)


class StatutUtilisateur(models.TextChoices):
    """Énumération des statuts possibles d'un utilisateur."""

    ACTIF = "ACTIF", "Actif"
    DESACTIVE = "DESACTIVE", "Désactivé"
    SUSPENDU = "SUSPENDU", "Suspendu"


class Permission(MyBaseModel):
    """
    Modèle Permission (privilège granulaire d'accès).
    Chaque fonctionnalité d'API est reliée à un code de permission unique.
    """

    code = models.CharField(max_length=100, unique=True, verbose_name="Code technique")
    libelle = models.CharField(max_length=255, verbose_name="Libellé")

    class Meta:
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"
        ordering = ["code"]

    def __str__(self):
        return f"{self.libelle} ({self.code})"

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        super().save(*args, **kwargs)


class Role(MyBaseModel):
    """
    Modèle Rôle regroupant un ensemble de permissions (Relation Many-to-Many).
    Exemples : Administrateur, Superviseur, Enquêteur.
    """

    libelle = models.CharField(max_length=100, unique=True, verbose_name="Libellé")
    permissions = models.ManyToManyField(
        Permission,
        related_name="roles",
        blank=True,
        verbose_name="Permissions associées",
    )

    class Meta:
        verbose_name = "Rôle"
        verbose_name_plural = "Rôles"
        ordering = ["libelle"]

    def __str__(self):
        return self.libelle


class Utilisateur(AbstractBaseUser, PermissionsMixin, MyBaseModel):
    """
    Modèle Utilisateur personnalisé conforme au diagramme UML.
    Hérite de AbstractBaseUser pour la gestion sécurisée de l'authentification et du mot de passe,
    de PermissionsMixin pour la compatibilité avec Django Admin et is_superuser,
    et de MyBaseModel pour l'audit automatique.
    """

    # Champs définis dans le diagramme
    nom = models.CharField(max_length=150, verbose_name="Nom de famille")
    prenom = models.CharField(max_length=150, verbose_name="Prénom")
    courriel = models.EmailField(unique=True, verbose_name="Adresse courriel")
    tel = models.CharField(max_length=30, blank=True, verbose_name="Numéro de téléphone")
    statut = models.CharField(
        max_length=20,
        choices=StatutUtilisateur.choices,
        default=StatutUtilisateur.ACTIF,
        verbose_name="Statut du compte",
    )

    # Champs techniques nécessaires à l'authentification et à l'administration Django
    is_staff = models.BooleanField(
        default=False,
        verbose_name="Accès administration",
        help_text="Indique si l'utilisateur peut se connecter au site d'administration.",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Actif",
        help_text="Indique si le compte est actif. Synchronisé automatiquement avec le statut métier.",
    )
    date_joined = models.DateTimeField(
        default=timezone.now,
        verbose_name="Date d'inscription",
    )

    # Relations du diagramme
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="utilisateurs",
        verbose_name="Rôle",
    )
    permissions = models.ManyToManyField(
        Permission,
        related_name="utilisateurs_directs",
        blank=True,
        verbose_name="Permissions directes",
    )

    # Résolution des collisions de groupes/permissions de Django natif (PermissionsMixin)
    groups = models.ManyToManyField(
        "auth.Group",
        related_name="utilisateurs_groupes",
        blank=True,
        verbose_name="Groupes Django",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="utilisateurs_permissions_django",
        blank=True,
        verbose_name="Permissions Django",
    )

    objects = UtilisateurManager()

    USERNAME_FIELD = "courriel"
    REQUIRED_FIELDS = ["nom", "prenom"]

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ["nom", "prenom"]

    def __str__(self):
        return f"{self.prenom} {self.nom} <{self.courriel}>"

    def get_full_name(self):
        """Retourne le prénom et le nom complet de l'utilisateur."""
        return f"{self.prenom} {self.nom}".strip()

    def get_short_name(self):
        """Retourne le prénom ou le courriel de l'utilisateur."""
        return self.prenom or self.courriel

    def clean(self):
        super().clean()
        if self.courriel:
            self.courriel = self.courriel.lower().strip()

    def save(self, *args, **kwargs):
        if self.courriel:
            self.courriel = self.courriel.lower().strip()
        # Synchronise automatiquement le booléen Django is_active avec le statut métier
        self.is_active = self.statut == StatutUtilisateur.ACTIF

        # Sécurise la mise à jour partielle avec update_fields
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = set(update_fields) | {"is_active", "courriel"}

        super().save(*args, **kwargs)

    def get_all_permissions_codes(self) -> set[str]:
        """
        Calcule les permissions effectives :
        - Un superutilisateur actif bénéficie de toutes les permissions du système.
        - Sinon, fusionne les permissions héritées du rôle et les permissions directes.
        """
        if self.is_superuser and self.is_active:
            return set(Permission.objects.values_list("code", flat=True))

        codes = set()
        if self.role_id:
            codes.update(self.role.permissions.values_list("code", flat=True))
        codes.update(self.permissions.values_list("code", flat=True))
        return codes
