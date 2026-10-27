from ninja.errors import HttpError


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
