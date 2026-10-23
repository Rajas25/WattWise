"""
/api/auth — Login, register, profile, logout
"""

import sqlite3
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from backend.config import settings
from backend.database import get_connection
from backend.models.schemas import LoginRequest, TokenResponse, UserCreate, UserOut
from backend.routers.deps import check_login_rate, get_current_user, _db_gen
from backend.security import (
    authenticate_user,
    create_access_token,
    get_user_by_email,
    hash_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/auth/token  — Login (JSON body)
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/token", response_model=TokenResponse)
def login(
    body: LoginRequest,
    request: Request,
    db: sqlite3.Connection = Depends(_db_gen),
):
    check_login_rate(request)
    user = authenticate_user(db, body.email.lower().strip(), body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    token = create_access_token(
        {"sub": str(user["id"]), "role": user["role"]},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return TokenResponse(
        access_token=token,
        role=user["role"],
        full_name=user["full_name"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/auth/register  — Self-register as student
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/register", response_model=UserOut, status_code=201)
def register(
    body: UserCreate,
    db: sqlite3.Connection = Depends(_db_gen),
):
    email = body.email.lower().strip()
    if get_user_by_email(db, email):
        raise HTTPException(status_code=409, detail="Email already registered")

    # Self-registration is always 'student' role
    hashed = hash_password(body.password)
    cur = db.execute(
        """
        INSERT INTO users (email, hashed_password, full_name, role)
        VALUES (?, ?, ?, 'student')
        """,
        (email, hashed, body.full_name),
    )
    user = db.execute(
        "SELECT * FROM users WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    return _user_row_to_out(user)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/auth/me  — Authenticated user profile
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/me", response_model=UserOut)
def get_me(current_user=Depends(get_current_user)):
    return _user_row_to_out(current_user)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/auth/logout  — Client-side; we just confirm
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/logout")
def logout(current_user=Depends(get_current_user)):
    return {"message": "Logged out. Please delete your local token."}


# ── helpers ───────────────────────────────────────────────────────────────────
def _user_row_to_out(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"],
        "role": row["role"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
    }
