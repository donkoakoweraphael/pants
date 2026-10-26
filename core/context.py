from contextvars import ContextVar
from typing import Optional

# Variable de contexte isolée pour chaque requête entrante (thread-safe et async-safe)
_current_user: ContextVar[Optional[object]] = ContextVar("current_user", default=None)


def set_current_user(user: Optional[object]) -> None:
    """Définit l'utilisateur courant pour la requête en cours."""
    _current_user.set(user)


def get_current_user() -> Optional[object]:
    """Récupère l'utilisateur courant associé au contexte de la requête."""
    return _current_user.get()


def reset_current_user() -> None:
    """Réinitialise la variable de contexte utilisateur."""
    _current_user.set(None)
