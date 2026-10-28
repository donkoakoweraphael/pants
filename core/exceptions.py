from django.utils.translation import gettext_lazy as _
from ninja.errors import HttpError, ValidationError
from ninja import NinjaAPI


class BaseAPIException(HttpError):
    """Exception de base personnalisée pour l'API avec statut HTTP et message structuré."""

    status_code: int = 400
    code: str = "BAD_REQUEST"

    def __init__(self, message: str = None, code: str = None, details=None):
        if message is None:
            message = _("Une erreur est survenue lors du traitement de la requête.")
        self.message = message
        if code:
            self.code = code
        self.details = details
        super().__init__(self.status_code, str(message))


class NotFoundException(BaseAPIException):
    status_code = 404
    code = "NOT_FOUND"

    def __init__(self, message: str = None, details=None):
        super().__init__(message=message or _("Ressource introuvable."), code=self.code, details=details)


class PermissionDeniedException(BaseAPIException):
    status_code = 403
    code = "FORBIDDEN"

    def __init__(self, message: str = None, details=None):
        super().__init__(message=message or _("Accès refusé."), code=self.code, details=details)


class UnauthorizedException(BaseAPIException):
    status_code = 401
    code = "UNAUTHORIZED"

    def __init__(self, message: str = None, details=None):
        super().__init__(message=message or _("Authentification requise."), code=self.code, details=details)


class ConflictException(BaseAPIException):
    status_code = 409
    code = "CONFLICT"

    def __init__(self, message: str = None, details=None):
        super().__init__(message=message or _("Conflit avec l'état actuel de la ressource."), code=self.code, details=details)


class PasswordChangeRequiredException(BaseAPIException):
    status_code = 403
    code = "PASSWORD_CHANGE_REQUIRED"

    def __init__(
        self,
        message: str = None,
        details=None,
    ):
        msg = message or _("Vous devez obligatoirement modifier votre mot de passe temporaire pour continuer.")
        super().__init__(message=msg, code=self.code, details=details)


def register_exception_handlers(api: NinjaAPI) -> None:
    """
    Enregistre les gestionnaires d'exceptions personnalisés sur l'instance NinjaAPI
    pour renvoyer des réponses JSON strictement conformes au schéma ApiErrorResponse.
    """

    @api.exception_handler(BaseAPIException)
    def on_base_api_exception(request, exc: BaseAPIException):
        return api.create_response(
            request,
            {
                "success": False,
                "message": str(exc.message),
                "code": exc.code,
                "details": exc.details,
            },
            status=exc.status_code,
        )

    @api.exception_handler(ValidationError)
    def on_validation_error(request, exc: ValidationError):
        return api.create_response(
            request,
            {
                "success": False,
                "message": str(_("Données de requête invalides ou incomplètes.")),
                "code": "VALIDATION_ERROR",
                "details": exc.errors,
            },
            status=422,
        )
