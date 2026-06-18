from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from mpost_api.auth import hash_password
from mpost_api.config import settings
from mpost_api.db import get_db
from mpost_api.repository import VALID_ROLES
from mpost_api.repository import assign_role as assign_role_record
from mpost_api.repository import list_user_roles
from mpost_api.repository import remove_role as remove_role_record
from mpost_api.repository import set_user_password

router = APIRouter()


class RoleAssignmentRequest(BaseModel):
    email: EmailStr
    role: str


class SetPasswordRequest(BaseModel):
    email: EmailStr
    password: str


class UserRolesResponse(BaseModel):
    email: str
    roles: list[str]


@router.post("/roles")
def assign_role(
    request: RoleAssignmentRequest,
    http_request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    # In production, check for rbac_admin role
    if settings.environment == "production":
        user_role = http_request.headers.get("X-MPOST-User-Role", "")
        if user_role != "rbac_admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if request.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Role must be one of: {', '.join(sorted(VALID_ROLES))}",
        )
    assign_role_record(db, str(request.email), request.role)
    return {"email": str(request.email), "role": request.role, "status": "assigned"}


@router.delete("/roles")
def remove_role(
    request: RoleAssignmentRequest,
    http_request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    # In production, check for rbac_admin role
    if settings.environment == "production":
        user_role = http_request.headers.get("X-MPOST-User-Role", "")
        if user_role != "rbac_admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if request.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Role must be one of: {', '.join(sorted(VALID_ROLES))}",
        )
    remove_role_record(db, str(request.email), request.role)
    return {"email": str(request.email), "role": request.role, "status": "removed"}


@router.post("/password")
def set_password(
    request: SetPasswordRequest,
    http_request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    # In production, check for rbac_admin role
    if settings.environment == "production":
        user_role = http_request.headers.get("X-MPOST-User-Role", "")
        if user_role != "rbac_admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if len(request.password) < 3:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 3 characters",
        )

    password_hash = hash_password(request.password)
    set_user_password(db, str(request.email), password_hash)
    return {"email": str(request.email), "status": "password_set"}


@router.get("/roles", response_model=list[UserRolesResponse])
def list_roles(
    http_request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> list[UserRolesResponse]:
    # In production, check for rbac_admin role
    if settings.environment == "production":
        user_role = http_request.headers.get("X-MPOST-User-Role", "")
        if user_role != "rbac_admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return [UserRolesResponse(**row) for row in list_user_roles(db)]
