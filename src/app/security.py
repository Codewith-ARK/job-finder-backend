import secrets
from collections.abc import Callable

from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session as DbSession

from .config import get_settings
from .database import get_db
from .models import Agency, AuthSession, User
from .services.auth_service import AuthContext, resolve_session, verify_csrf
from .services.errors import Forbidden, Unauthorized

STAFF_ROLES = ("employee", "supervisor")


def get_auth_context(request: Request, db: DbSession = Depends(get_db)) -> AuthContext:
    token = request.cookies.get(get_settings().session_cookie)
    context = resolve_session(db, token)
    if not context:
        raise Unauthorized()
    return context


def require_csrf(request: Request, context: AuthContext = Depends(get_auth_context)) -> AuthContext:
    header = request.headers.get("x-csrf-token")
    cookie = request.cookies.get(get_settings().csrf_cookie)
    if not header or not cookie or not secrets.compare_digest(header, cookie):
        raise Forbidden("The request could not be verified. Refresh and try again.")
    if not verify_csrf(context.session, header):
        raise Forbidden("The request could not be verified. Refresh and try again.")
    return context


def current_candidate(context: AuthContext = Depends(get_auth_context)) -> AuthContext:
    if context.user.role != "candidate":
        raise Forbidden("This workspace is for candidates.")
    return context


def current_staff(context: AuthContext = Depends(get_auth_context)) -> AuthContext:
    if context.user.role not in STAFF_ROLES:
        raise Forbidden("This workspace is for agency staff.")
    return context


def current_agency_user(
    context: AuthContext = Depends(get_auth_context),
) -> AuthContext:
    if context.user.role not in ("candidate", *STAFF_ROLES):
        raise Forbidden("This workspace is for agency members.")
    return context


def current_platform_admin(
    context: AuthContext = Depends(get_auth_context),
) -> AuthContext:
    if context.user.role != "platform_admin":
        raise Forbidden("This workspace is for platform administrators.")
    return context


def require_candidate(context: AuthContext = Depends(require_csrf)) -> AuthContext:
    if context.user.role != "candidate":
        raise Forbidden("This workspace is for candidates.")
    return context


def require_staff(context: AuthContext = Depends(require_csrf)) -> AuthContext:
    if context.user.role not in STAFF_ROLES:
        raise Forbidden("This workspace is for agency staff.")
    return context


def require_supervisor(context: AuthContext = Depends(require_csrf)) -> AuthContext:
    if context.user.role != "supervisor":
        raise Forbidden("This action requires a supervisor.")
    return context


def require_platform_admin(
    context: AuthContext = Depends(require_csrf),
) -> AuthContext:
    if context.user.role != "platform_admin":
        raise Forbidden("This workspace is for platform administrators.")
    return context


def require_agency(context: AuthContext) -> Agency:
    if context.agency is None:
        raise Forbidden("Select an agency to continue.")
    return context.agency


def role_dependency(*roles: str) -> Callable[..., AuthContext]:
    def dependency(context: AuthContext = Depends(require_csrf)) -> AuthContext:
        if context.user.role not in roles:
            raise Forbidden("You do not have access to this action.")
        return context

    return dependency


def origin_allowed(request: Request) -> bool:
    """Accept allowlisted origins, plus the API's own origin for local docs testing."""
    origin = request.headers.get("origin")
    if not origin:
        return True
    settings = get_settings()
    if origin in settings.cors_origin_list:
        return True
    if settings.docs_testing_enabled:
        return origin == f"{request.url.scheme}://{request.url.netloc}"
    return False


def enforce_origin(request: Request) -> None:
    if not origin_allowed(request):
        raise Forbidden("This origin is not allowed.")


def set_session_cookies(response: Response, token: str, csrf: str) -> None:
    settings = get_settings()
    max_age = settings.session_days * 24 * 60 * 60
    response.set_cookie(
        settings.session_cookie,
        token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    response.set_cookie(
        settings.csrf_cookie,
        csrf,
        max_age=max_age,
        httponly=False,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


def clear_session_cookies(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(settings.session_cookie, path="/")
    response.delete_cookie(settings.csrf_cookie, path="/")


__all__ = [
    "AuthContext",
    "Agency",
    "AuthSession",
    "User",
    "clear_session_cookies",
    "current_agency_user",
    "current_candidate",
    "current_platform_admin",
    "current_staff",
    "enforce_origin",
    "get_auth_context",
    "origin_allowed",
    "require_agency",
    "require_candidate",
    "require_csrf",
    "require_platform_admin",
    "require_staff",
    "require_supervisor",
    "role_dependency",
    "set_session_cookies",
]
