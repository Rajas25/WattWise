"""
WattWise — Create First Admin Account
========================================
Run this script once from the project root to create your local administrator.

Usage:
    python backend/create_admin.py

You will be prompted for email, full name, and password (not echoed).
The account is created directly in the local SQLite database.
No credentials are written to source code or log files.
"""

import sys
import getpass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import settings
from backend.database import init_db, get_connection
from backend.security import get_user_by_email, hash_password


def main():
    print("=" * 55)
    print("  WattWise — Create Administrator Account")
    print("=" * 55)
    print(f"  Database: {settings.DATABASE_URL}")
    print("=" * 55)

    # Ensure DB is initialized
    init_db()

    email = input("Admin email: ").strip().lower()
    if not email or "@" not in email:
        print("ERROR: Invalid email address.")
        sys.exit(1)

    full_name = input("Full name: ").strip()
    if not full_name:
        print("ERROR: Full name cannot be empty.")
        sys.exit(1)

    password = getpass.getpass("Password (min 8 chars): ")
    if len(password) < 8:
        print("ERROR: Password must be at least 8 characters.")
        sys.exit(1)

    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("ERROR: Passwords do not match.")
        sys.exit(1)

    conn = get_connection()
    try:
        existing = get_user_by_email(conn, email)
        if existing:
            print(f"ERROR: A user with email '{email}' already exists.")
            sys.exit(1)

        hashed = hash_password(password)
        conn.execute(
            "INSERT INTO users (email, hashed_password, full_name, role) VALUES (?, ?, ?, 'admin')",
            (email, hashed, full_name),
        )
        conn.commit()
        print(f"\n✅ Admin account created successfully!")
        print(f"   Email : {email}")
        print(f"   Name  : {full_name}")
        print(f"   Role  : admin")
        print(f"\nYou can now log in at http://localhost:8000/auth.html")
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
