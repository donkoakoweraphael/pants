from django.contrib import admin
from accounts.models import Utilisateur, Role, Permission


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "code",
        "libelle",
        "get_roles_count",
        "cree_par",
        "modifie_par",
        "date_creation",
        "date_modification",
    )
    list_display_links = ("id", "code", "libelle")
    search_fields = ("code", "libelle")
    ordering = ("id",)
    readonly_fields = (
        "id",
        "get_roles_display",
        "cree_par",
        "modifie_par",
        "date_creation",
        "date_modification",
    )
    fieldsets = (
        (
            "Identifiant & Informations générales",
            {"fields": ("id", "code", "libelle")},
        ),
        (
            "Relations (Rôles)",
            {"fields": ("get_roles_display",)},
        ),
        (
            "Traçabilité (Audit)",
            {
                "fields": (
                    "cree_par",
                    "modifie_par",
                    "date_creation",
                    "date_modification",
                )
            },
        ),
    )

    @admin.display(description="Nombre de rôles")
    def get_roles_count(self, obj):
        return obj.roles.count()

    @admin.display(description="Rôles associés à cette permission")
    def get_roles_display(self, obj):
        if not obj.pk:
            return "Enregistrez d'abord la permission pour associer des rôles."
        roles = obj.roles.all()
        if not roles.exists():
            return "Aucun rôle associé actuellement"
        return ", ".join([r.libelle for r in roles])


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "libelle",
        "get_permissions_count",
        "get_utilisateurs_count",
        "cree_par",
        "modifie_par",
        "date_creation",
        "date_modification",
    )
    list_display_links = ("id", "libelle")
    search_fields = ("libelle",)
    filter_horizontal = ("permissions",)
    ordering = ("id",)
    readonly_fields = (
        "id",
        "get_utilisateurs_display",
        "cree_par",
        "modifie_par",
        "date_creation",
        "date_modification",
    )
    fieldsets = (
        (
            "Identifiant & Informations générales",
            {"fields": ("id", "libelle", "permissions")},
        ),
        (
            "Membres (Utilisateurs)",
            {"fields": ("get_utilisateurs_display",)},
        ),
        (
            "Traçabilité (Audit)",
            {
                "fields": (
                    "cree_par",
                    "modifie_par",
                    "date_creation",
                    "date_modification",
                )
            },
        ),
    )

    @admin.display(description="Permissions")
    def get_permissions_count(self, obj):
        return obj.permissions.count()

    @admin.display(description="Utilisateurs")
    def get_utilisateurs_count(self, obj):
        return obj.utilisateurs.count()

    @admin.display(description="Utilisateurs assignés à ce rôle")
    def get_utilisateurs_display(self, obj):
        if not obj.pk:
            return "Enregistrez d'abord le rôle pour lui associer des utilisateurs."
        utilisateurs = obj.utilisateurs.all()
        count = utilisateurs.count()
        if count == 0:
            return "Aucun utilisateur assigné à ce rôle actuellement"
        noms = [u.get_full_name() or u.courriel for u in utilisateurs[:10]]
        suffix = f" (et {count - 10} autre(s)...)" if count > 10 else ""
        return ", ".join(noms) + suffix


@admin.register(Utilisateur)
class UtilisateurAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "courriel",
        "nom",
        "prenom",
        "tel",
        "statut",
        "role",
        "is_staff",
        "is_active",
        "doit_changer_mot_de_passe",
        "cree_par",
        "modifie_par",
        "date_creation",
        "date_modification",
    )
    list_display_links = ("id", "courriel")
    list_filter = ("statut", "role", "is_staff", "is_active", "doit_changer_mot_de_passe")
    search_fields = ("courriel", "nom", "prenom", "tel")
    filter_horizontal = ("permissions", "groups", "user_permissions")
    ordering = ("id",)
    readonly_fields = (
        "id",
        "cree_par",
        "modifie_par",
        "date_creation",
        "date_modification",
        "last_login",
        "date_joined",
    )
    fieldsets = (
        (
            "Identifiant & Informations personnelles",
            {"fields": ("id", "courriel", "password", "nom", "prenom", "tel")},
        ),
        (
            "Statut & Rôles",
            {"fields": ("statut", "role", "permissions")},
        ),
        (
            "Permissions Django & Administration",
            {
                "fields": (
                    "is_staff",
                    "is_superuser",
                    "is_active",
                    "doit_changer_mot_de_passe",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Traçabilité (Audit)",
            {
                "fields": (
                    "cree_par",
                    "modifie_par",
                    "date_creation",
                    "date_modification",
                )
            },
        ),
        (
            "Connexions & Sessions",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                )
            },
        ),
    )
