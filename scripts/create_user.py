#!/usr/bin/env python3
"""Create a user with password in the database."""
import sys
import psycopg
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_user(email: str, password: str, display_name: str = None, role: str = "user"):
    """Create a user with the given email and password."""
    password_hash = pwd_context.hash(password)
    
    with psycopg.connect("postgresql://mpost:mpost@localhost:55432/mpost") as conn:
        # Insert user
        user_result = conn.execute(
            """
            INSERT INTO users (email, display_name, password_hash)
            VALUES (%s, %s, %s)
            ON CONFLICT (email) DO UPDATE
            SET password_hash = EXCLUDED.password_hash, display_name = EXCLUDED.display_name
            RETURNING id
            """,
            (email, display_name, password_hash)
        ).fetchone()
        
        user_id = user_result[0]
        
        # Get or create role
        role_result = conn.execute(
            "SELECT id FROM roles WHERE name = %s",
            (role,)
        ).fetchone()
        
        if not role_result:
            role_result = conn.execute(
                "INSERT INTO roles (name) VALUES (%s) RETURNING id",
                (role,)
            ).fetchone()
        
        role_id = role_result[0]
        
        # Assign role
        conn.execute(
            """
            INSERT INTO user_roles (user_id, role_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (user_id, role_id)
        )
        
        conn.commit()
        print(f"✅ Created user: {email} with role: {role}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_user.py <email> <password> [display_name] [role]")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    display_name = sys.argv[3] if len(sys.argv) > 3 else None
    role = sys.argv[4] if len(sys.argv) > 4 else "user"
    
    create_user(email, password, display_name, role)
