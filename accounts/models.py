from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from core.models import MyBaseModel


class UtilisateurManager(BaseUserManager):
    """Gestionnaire personnalisé pour créer des utilisateurs avec leur courriel comme identifiant."""

    def create_user(self, courriel, password=None, **extra_fields):
        if not courriel:
            raise ValueError("Le champ courriel est obligatoire.")
        courriel = self.normalize_email(courriel)
        extra_fields.setdefault("statut", StatutUtilisateur.ACTIF)
        user = self.model(courriel=courriel, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, courriel, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("statut", StatutUtilisateur.ACTIF)

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


class Utilisateur(AbstractUser, MyBaseModel):
    """
    Modèle Utilisateur personnalisé conforme au diagramme UML.
    Identifié uniquement par son courriel. Possède un rôle et des permissions directes.
    """

    # Retrait du champ username au profit du courriel
    username = None
    first_name = None
    last_name = None
    email = None

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

    # Résolution des collisions de groupes/permissions de Django natif
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

    def save(self, *args, **kwargs):
        # Synchronise automatiquement le booléen Django is_active avec le statut métier
        self.is_active = self.statut == StatutUtilisateur.ACTIF
        super().save(*args, **kwargs)

    def get_all_permissions_codes(self) -> set[str]:
        """
        Calcule les permissions effectives : fusionne les permissions
        héritées du rôle et les permissions directes de l'utilisateur.
        """
        codes = set()
        if self.role_id:
            codes.update(self.role.permissions.values_list("code", flat=True))
        codes.update(self.permissions.values_list("code", flat=True))
        return codes
