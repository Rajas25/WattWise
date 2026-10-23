"""
WattWise Security — Password hashing and JWT token handling.

Uses bcrypt 5.x directly (bypasses passlib which is incompatible with bcrypt 5.x
on Python 3.14). All passwords are UTF-8 encoded and bcrypt handles up to 72 bytes;
passwords longer than 72 chars are SHA-256 pre-hashed before bcrypt to avoid silent
truncation (OWASP-recommended approach).
"""

import hashlib
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from backend.config import settings


# ── Internal: stretch long passwords safely ───────────────────────────────────
def _prepare_password(plain: str) -> bytes:
    """
    Converts a plaintext password to bytes safe for bcrypt.
    Passwords > 72 bytes are SHA-256 pre-hashed (hex string) then bcrypt'd.
    This prevents silent truncation while keeping bcrypt's slow-hash properties.
    """
    raw = plain.encode("utf-8")
    if len(raw) > 72:
        raw = hashlib.sha256(raw).hexdigest().encode("utf-8")
    return raw


# ── Password hashing ──────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    """Returns a bcrypt hash string for the given plaintext password."""
    hashed = bcrypt.hashpw(_prepare_password(plain), bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Returns True if the plaintext matches the stored bcrypt hash."""
    try:
        return bcrypt.checkpw(_prepare_password(plain), hashed.encode("utf-8"))
    except Exception:
        return False


# ── JWT tokens ────────────────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload.update({"exp": expire})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Returns decoded payload dict, or None on any error (expired, invalid, tampered)."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


# ── User lookup helpers ───────────────────────────────────────────────────────
def get_user_by_email(conn: sqlite3.Connection, email: str) -> Optional[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return conn.execute(
        "SELECT * FROM users WHERE email = ? AND is_active = 1", (email,)
    ).fetchone()


def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> Optional[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return conn.execute(
        "SELECT * FROM users WHERE id = ? AND is_active = 1", (user_id,)
    ).fetchone()


def authenticate_user(
    conn: sqlite3.Connection, email: str, password: str
) -> Optional[sqlite3.Row]:
    """Returns the user row on successful authentication, None otherwise."""
    user = get_user_by_email(conn, email)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user
