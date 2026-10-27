from django.contrib import admin
from accounts.models import Utilisateur, Role, Permission


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "libelle",
        "cree_par",
        "date_creation",
        "date_modification",
    )
    search_fields = ("code", "libelle")
    ordering = ("code",)
    readonly_fields = ("cree_par", "modifie_par", "date_creation", "date_modification")
    fieldsets = (
        ("Informations générales", {"fields": ("code", "libelle")}),
        (
            "Traçabilité (Audit)",
            {"fields": ("cree_par", "modifie_par", "date_creation", "date_modification")},
        ),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = (
        "libelle",
        "get_permissions_count",
        "cree_par",
        "date_creation",
        "date_modification",
    )
    search_fields = ("libelle",)
    filter_horizontal = ("permissions",)
    ordering = ("libelle",)
    readonly_fields = ("cree_par", "modifie_par", "date_creation", "date_modification")
    fieldsets = (
        ("Informations générales", {"fields": ("libelle", "permissions")}),
        (
            "Traçabilité (Audit)",
            {"fields": ("cree_par", "modifie_par", "date_creation", "date_modification")},
        ),
    )

    @admin.display(description="Nombre de permissions")
    def get_permissions_count(self, obj):
        return obj.permissions.count()


@admin.register(Utilisateur)
class UtilisateurAdmin(admin.ModelAdmin):
    list_display = (
        "courriel",
        "nom",
        "prenom",
        "statut",
        "role",
        "is_staff",
        "is_active",
        "cree_par",
        "date_creation",
    )
    list_filter = ("statut", "role", "is_staff", "is_active")
    search_fields = ("courriel", "nom", "prenom", "tel")
    filter_horizontal = ("permissions", "groups", "user_permissions")
    ordering = ("nom", "prenom")
    readonly_fields = (
        "last_login",
        "date_joined",
        "cree_par",
        "modifie_par",
        "date_creation",
        "date_modification",
    )
    fieldsets = (
        (
            "Identifiants & Informations personnelles",
            {"fields": ("courriel", "password", "nom", "prenom", "tel")},
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
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Traçabilité & Connexions (Audit)",
            {
                "fields": (
                    "cree_par",
                    "modifie_par",
                    "date_creation",
                    "date_modification",
                    "last_login",
                    "date_joined",
                )
            },
        ),
    )
