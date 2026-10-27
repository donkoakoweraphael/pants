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


@api.get("/add")
def add(request, a: int, b: int):
    return {"result": a + b}


@api.get("/health", summary="Vérification de l'état du service", tags=["Système"])
def health_check(request):
    """Endpoint de santé pour vérifier que l'API est en ligne."""
    return {"status": "ok", "service": "pants-api"}


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]