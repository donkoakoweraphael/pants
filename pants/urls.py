"""
URL configuration for pants project.
"""

from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI
from core.exceptions import register_exception_handlers

# Instance centrale de l'API Ninja avec métadonnées complètes pour Swagger
api = NinjaAPI(
    title="PANTS API",
    version="1.0.0",
    description="API de collecte terrain et gestion des sites / établissements",
    docs_url="/docs",
)

# Enregistrement des gestionnaires d'exceptions personnalisés
register_exception_handlers(api)


@api.get("/health", summary="Vérification de l'état du service", tags=["Système"])
def health_check(request):
    """Endpoint de santé pour vérifier que l'API est en ligne."""
    return {"status": "ok", "service": "pants-api"}


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]