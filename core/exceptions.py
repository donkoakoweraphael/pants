from ninja.errors import HttpError
from ninja import NinjaAPI


class BaseAPIException(HttpError):
    """Exception de base personnalisée pour l'API avec statut HTTP et message structuré."""

    status_code: int = 400
    code: str = "BAD_REQUEST"

    def __init__(self, message: str, code: str = None, details=None):
        self.message = message
        if code:
            self.code = code
        self.details = details
        super().__init__(self.status_code, message)


class NotFoundException(BaseAPIException):
    status_code = 404
    code = "NOT_FOUND"


class PermissionDeniedException(BaseAPIException):
    status_code = 403
    code = "FORBIDDEN"


class UnauthorizedException(BaseAPIException):
    status_code = 401
    code = "UNAUTHORIZED"


class ConflictException(BaseAPIException):
    status_code = 409
    code = "CONFLICT"


class PasswordChangeRequiredException(BaseAPIException):
    status_code = 403
    code = "PASSWORD_CHANGE_REQUIRED"

    def __init__(
        self,
        message: str = "Vous devez obligatoirement modifier votre mot de passe temporaire pour continuer.",
        details=None,
    ):
        super().__init__(message=message, code="PASSWORD_CHANGE_REQUIRED", details=details)


def register_exception_handlers(api: NinjaAPI) -> None:
    """
    Enregistre les gestionnaires d'exceptions personnalisés sur l'instance NinjaAPI
    pour renvoyer des réponses JSON conformes au schéma ErrorResponse.
    """

    @api.exception_handler(BaseAPIException)
    def on_base_api_exception(request, exc: BaseAPIException):
        return api.create_response(
            request,
            {
                "message": exc.message,
                "code": exc.code,
                "details": exc.details,
            },
            status=exc.status_code,
        )
