import sqlite3
import secrets
import hashlib
from typing import Optional, Dict, Any

from app.config import DB_PATH


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def init_db():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.commit()


def hash_password(password: str, salt: Optional[str] = None) -> Dict[str, str]:
    if salt is None:
        salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200_000
    ).hex()

    return {
        "salt": salt,
        "password_hash": password_hash
    }


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    generated = hash_password(password, salt)["password_hash"]

    return secrets.compare_digest(generated, expected_hash)


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, username, name, password_hash, salt, is_active
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def create_user(username: str, password: str, name: str, is_active: int = 1) -> None:
    password_data = hash_password(password)

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO users (
                username,
                name,
                password_hash,
                salt,
                is_active
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                username,
                name,
                password_data["password_hash"],
                password_data["salt"],
                is_active
            )
        )

        connection.commit()


def ensure_demo_user():
    existing_user = get_user_by_username("demo")

    if existing_user:
        return

    create_user(
        username="demo",
        password="demo123",
        name="Usuario Demo",
        is_active=1
    )
