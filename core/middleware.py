import logging
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from django.conf import settings
from core.context import set_current_user, reset_current_user

logger = logging.getLogger(__name__)


class CurrentUserMiddleware(MiddlewareMixin):
    """
    Middleware qui résout l'utilisateur authentifié (Session Django ou Bearer JWT)
    et le place dans le contexte thread-safe pour les modèles (audit automatique).
    """

    def process_request(self, request):
        user = None

        # 1. Résolution par session Django (ex: Django Admin)
        if hasattr(request, "user") and getattr(request.user, "is_authenticated", False):
            user = request.user

        # 2. Résolution par Token JWT (Authorization: Bearer <token>)
        if not user:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1].strip()
                try:
                    import jwt

                    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                    user_id = payload.get("user_id")
                    if user_id is not None:
                        User = get_user_model()
                        user = User.objects.filter(id=user_id, is_active=True).first()
                except ImportError:
                    logger.warning("Le package PyJWT n'est pas encore installé pour décoder les tokens JWT.")
                except Exception as exc:
                    logger.debug(f"Échec de décodage du token JWT dans CurrentUserMiddleware: {exc}")

        # Injecte l'utilisateur résolu (ou None) dans le contexte
        set_current_user(user)

    def process_response(self, request, response):
        # Nettoyage du contexte à la fin de la requête
        reset_current_user()
        return response

    def process_exception(self, request, exception):
        # Nettoyage même en cas d'exception non gérée
        reset_current_user()
