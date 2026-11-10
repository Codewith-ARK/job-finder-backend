from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session as DbSession

from ..config import get_settings
from ..database import get_db
from ..schemas.auth_schema import (
    ContextInput,
    DemoLoginInput,
    DemoPersonaOut,
    LoginInput,
    PasswordChangeInput,
    RegisterInput,
    SessionOut,
)
from ..security import (
    clear_session_cookies,
    enforce_origin,
    require_csrf,
    set_session_cookies,
)
from ..services import auth_service
from ..services.errors import NotFound

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/session", response_model=SessionOut | None)
def read_session(request: Request, db: DbSession = Depends(get_db)) -> SessionOut | None:
    token = request.cookies.get(get_settings().session_cookie)
    context = auth_service.resolve_session(db, token)
    return auth_service.session_out(db, context) if context else None


@router.get("/demo-personas", response_model=list[DemoPersonaOut])
def read_demo_personas(db: DbSession = Depends(get_db)) -> list[DemoPersonaOut]:
    if not get_settings().demo_login_enabled:
        raise NotFound("Demo sign-in is not enabled.")
    return auth_service.demo_personas(db)


@router.post(
    "/register",
    response_model=SessionOut,
    dependencies=[Depends(enforce_origin)],
)
def register(
    payload: RegisterInput, response: Response, db: DbSession = Depends(get_db)
) -> SessionOut:
    context, token, csrf = auth_service.register(db, payload.name, payload.email, payload.password)
    set_session_cookies(response, token, csrf)
    return auth_service.session_out(db, context)


@router.post("/login", response_model=SessionOut, dependencies=[Depends(enforce_origin)])
def login(payload: LoginInput, response: Response, db: DbSession = Depends(get_db)) -> SessionOut:
    context, token, csrf = auth_service.login(
        db, payload.email, payload.password, payload.agency_id
    )
    set_session_cookies(response, token, csrf)
    return auth_service.session_out(db, context)


@router.post("/demo-login", response_model=SessionOut, dependencies=[Depends(enforce_origin)])
def demo_login(
    payload: DemoLoginInput, response: Response, db: DbSession = Depends(get_db)
) -> SessionOut:
    context, token, csrf = auth_service.demo_login(db, payload.persona_id)
    set_session_cookies(response, token, csrf)
    return auth_service.session_out(db, context)


@router.post("/context", response_model=SessionOut)
def switch_context(
    payload: ContextInput,
    context=Depends(require_csrf),
    db: DbSession = Depends(get_db),
) -> SessionOut:
    updated = auth_service.switch_agency(db, context, payload.agency_id)
    return auth_service.session_out(db, updated)


@router.post("/password", status_code=204)
def change_password(
    payload: PasswordChangeInput,
    response: Response,
    context=Depends(require_csrf),
    db: DbSession = Depends(get_db),
) -> None:
    auth_service.change_password(db, context, payload.current_password, payload.new_password)
    # FastAPI merges headers set on the injected Response into the final response.
    clear_session_cookies(response)


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    context=Depends(require_csrf),
    db: DbSession = Depends(get_db),
) -> None:
    auth_service.logout(db, context)
    clear_session_cookies(response)
