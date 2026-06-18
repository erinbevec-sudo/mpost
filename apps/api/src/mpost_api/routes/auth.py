"""Authentication routes."""
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.orm import Session

from mpost_api.auth import create_session, delete_session, get_session_user, verify_password
from mpost_api.config import settings
from mpost_api.db import get_db

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    email: str
    display_name: str | None
    roles: list[str]


class CurrentUserResponse(BaseModel):
    email: str
    display_name: str | None
    roles: list[str]
    authenticated: bool


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Login with email and password."""
    # Get user from database
    result = db.execute(
        text("""
            SELECT
                u.id,
                u.email,
                u.display_name,
                u.password_hash,
                ARRAY_AGG(r.name) as roles
            FROM users u
            LEFT JOIN user_roles ur ON u.id = ur.user_id
            LEFT JOIN roles r ON ur.role_id = r.id
            WHERE u.email = :email
            GROUP BY u.id, u.email, u.display_name, u.password_hash
        """),
        {"email": request.email}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id, email, display_name, password_hash, roles = result

    # Check password
    if not password_hash or not verify_password(request.password, password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create session
    session_token = create_session(db, str(user_id))

    # Set httponly cookie
    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=7 * 24 * 60 * 60,  # 7 days
    )

    return LoginResponse(
        email=email,
        display_name=display_name,
        roles=[r for r in roles if r] if roles else []
    )


@router.post("/logout")
def logout(response: Response, session: str | None = Cookie(default=None), db: Session = Depends(get_db)):
    """Logout and invalidate session."""
    if session:
        delete_session(db, session)

    response.delete_cookie(key="session")
    return {"message": "Logged out successfully"}


@router.get("/current-user", response_model=CurrentUserResponse)
def current_user(session: str | None = Cookie(default=None), db: Session = Depends(get_db)):
    """Get current user information."""
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = get_session_user(db, session)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return CurrentUserResponse(
        email=user["email"],
        display_name=user["display_name"],
        roles=user["roles"],
        authenticated=True
    )
