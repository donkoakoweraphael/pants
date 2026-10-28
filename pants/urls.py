"""
URL configuration for pants project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path
from ninja import NinjaAPI
from ninja.openapi.docs import Redoc
from core.exceptions import register_exception_handlers
from accounts.api import (
    router_auth,
    router_permissions,
    router_roles,
    router_utilisateurs,
)

# Instance centrale de l'API Ninja avec métadonnées complètes pour Swagger
api = NinjaAPI(
    title="PANTS API",
    version="1.0.0",
    description="API de collecte terrain et gestion des sites / établissements",
    docs_url="/docs",
)

# Instance du visualiseur de documentation alternative Redoc
redoc_viewer = Redoc()


def redoc_view(request):
    """Affiche la documentation interactive alternative Redoc."""
    return redoc_viewer.render_page(request, api)

# Enregistrement des gestionnaires d'exceptions personnalisés
register_exception_handlers(api)

# Enregistrement des routeurs REST au premier niveau de l'API
api.add_router("/auth", router_auth, tags=["Authentification"])
api.add_router("/permissions", router_permissions, tags=["Permissions"])
api.add_router("/roles", router_roles, tags=["Rôles"])
api.add_router("/utilisateurs", router_utilisateurs, tags=["Utilisateurs"])


@api.get("/add")
def add(request, a: int, b: int):
    return {"result": a + b}


@api.get("/health", summary="Vérification de l'état du service", tags=["Système"])
def health_check(request):
    """Endpoint de santé pour vérifier que l'API est en ligne."""
    return {"status": "ok", "service": "pants-api"}


urlpatterns = [
    path("admin/", admin.site.urls),
    re_path(r"^api/redoc/?$", redoc_view, name="redoc"),
    path("api/", api.urls),
]