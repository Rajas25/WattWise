"""
/api/users — Admin-only user management
"""

import sqlite3
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from backend.models.schemas import UserCreate, UserOut, UserUpdate
from backend.routers.deps import _db_gen, require_admin
from backend.security import get_user_by_email, hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/", response_model=List[UserOut])
def list_users(
    db: sqlite3.Connection = Depends(_db_gen),
    _=Depends(require_admin),
):
    rows = db.execute(
        "SELECT * FROM users ORDER BY created_at DESC"
    ).fetchall()
    return [_row_to_out(r) for r in rows]


@router.post("/", response_model=UserOut, status_code=201)
def create_user(
    body: UserCreate,
    db: sqlite3.Connection = Depends(_db_gen),
    _=Depends(require_admin),
):
    email = body.email.lower().strip()
    if get_user_by_email(db, email):
        raise HTTPException(status_code=409, detail="Email already registered")
    hashed = hash_password(body.password)
    cur = db.execute(
        "INSERT INTO users (email, hashed_password, full_name, role) VALUES (?, ?, ?, ?)",
        (email, hashed, body.full_name, body.role),
    )
    row = db.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _row_to_out(row)


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: sqlite3.Connection = Depends(_db_gen),
    _=Depends(require_admin),
):
    row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return _row_to_out(row)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserUpdate,
    db: sqlite3.Connection = Depends(_db_gen),
    _=Depends(require_admin),
):
    row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    updates = {}
    if body.full_name is not None:
        updates["full_name"] = body.full_name
    if body.role is not None:
        updates["role"] = body.role
    if body.is_active is not None:
        updates["is_active"] = int(body.is_active)

    if not updates:
        return _row_to_out(row)

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [user_id]
    db.execute(
        f"UPDATE users SET {set_clause}, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id = ?",
        values,
    )
    updated = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _row_to_out(updated)


@router.delete("/{user_id}", status_code=204)
def deactivate_user(
    user_id: int,
    db: sqlite3.Connection = Depends(_db_gen),
    current_user=Depends(require_admin),
):
    if current_user["id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    db.execute(
        "UPDATE users SET is_active = 0, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id = ?",
        (user_id,),
    )


def _row_to_out(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"],
        "role": row["role"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
    }
