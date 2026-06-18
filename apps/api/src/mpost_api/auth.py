"""Authentication and session management."""
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import text
from sqlalchemy.orm import Session


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_session(db: Session, user_id: str, expiry_hours: int = 168) -> str:
    """
    Create a new session for a user.

    Args:
        db: Database session
        user_id: User ID
        expiry_hours: Session expiry in hours (default 7 days)

    Returns:
        Session token
    """
    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)

    db.execute(
        text("""
            INSERT INTO sessions (user_id, session_token, expires_at)
            VALUES (:user_id, :session_token, :expires_at)
        """),
        {"user_id": user_id, "session_token": session_token, "expires_at": expires_at}
    )
    db.commit()

    return session_token


def get_session_user(db: Session, session_token: str) -> dict | None:
    """
    Get user information from a session token.

    Returns:
        User dict with id, email, display_name, roles or None if invalid/expired
    """
    result = db.execute(
        text("""
            SELECT
                u.id,
                u.email,
                u.display_name,
                ARRAY_AGG(r.name) as roles
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            LEFT JOIN user_roles ur ON u.id = ur.user_id
            LEFT JOIN roles r ON ur.role_id = r.id
            WHERE s.session_token = :token
              AND s.expires_at > NOW()
            GROUP BY u.id, u.email, u.display_name
        """),
        {"token": session_token}
    ).fetchone()

    if not result:
        return None

    # Update last accessed time
    db.execute(
        text("""
            UPDATE sessions
            SET last_accessed_at = NOW()
            WHERE session_token = :token
        """),
        {"token": session_token}
    )
    db.commit()

    return {
        "id": str(result[0]),
        "email": result[1],
        "display_name": result[2],
        "roles": [r for r in result[3] if r] if result[3] else []
    }


def delete_session(db: Session, session_token: str) -> None:
    """Delete a session (logout)."""
    db.execute(
        text("DELETE FROM sessions WHERE session_token = :token"),
        {"token": session_token}
    )
    db.commit()


def cleanup_expired_sessions(db: Session) -> int:
    """Delete all expired sessions. Returns number of deleted sessions."""
    result = db.execute(
        text("DELETE FROM sessions WHERE expires_at < NOW()")
    )
    db.commit()
    return result.rowcount
