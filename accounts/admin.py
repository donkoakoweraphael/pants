from django.contrib import admin
from accounts.models import Utilisateur, Role, Permission


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("code", "libelle", "date_creation", "date_modification")
    search_fields = ("code", "libelle")
    ordering = ("code",)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("libelle", "get_permissions_count", "date_creation", "date_modification")
    search_fields = ("libelle",)
    filter_horizontal = ("permissions",)
    ordering = ("libelle",)

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
        "date_creation",
    )
    list_filter = ("statut", "role", "is_staff", "is_active")
    search_fields = ("courriel", "nom", "prenom", "tel")
    filter_horizontal = ("permissions", "groups", "user_permissions")
    ordering = ("nom", "prenom")
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
            "Audit & Connexions",
            {"fields": ("last_login", "date_joined")},
        ),
    )
    readonly_fields = ("last_login", "date_joined")
