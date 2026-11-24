"""Autentikasi sederhana menggunakan password hash dan token bertanda tangan."""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

PASSWORD_ITERATIONS = 310_000
TOKEN_LIFETIME_SECONDS = 60 * 60 * 8
DEVELOPMENT_SECRET_KEY = "development-only-change-this-secret"


def load_secret_key(environment: str, configured_key: str | None) -> str:
    """Gunakan secret kuat saat production; fallback hanya untuk development lokal."""
    if environment.lower() == "production":
        if not configured_key or configured_key == DEVELOPMENT_SECRET_KEY:
            raise RuntimeError(
                "JEJAKKBM_SECRET_KEY wajib diatur dengan nilai rahasia saat production."
            )
        if len(configured_key) < 32:
            raise RuntimeError(
                "JEJAKKBM_SECRET_KEY production minimal 32 karakter."
            )
        return configured_key
    return configured_key or DEVELOPMENT_SECRET_KEY


APP_ENVIRONMENT = os.getenv("JEJAKKBM_ENV", "development")
SECRET_KEY = load_secret_key(
    APP_ENVIRONMENT, os.getenv("JEJAKKBM_SECRET_KEY")
)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return (
        f"pbkdf2_sha256\u0024{PASSWORD_ITERATIONS}\u0024"
        f"{salt.hex()}\u0024{password_hash.hex()}"
    )


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    try:
        algorithm, iterations, salt_hex, expected_hash = stored_hash.split("\u0024")
        if algorithm != "pbkdf2_sha256":
            return False
        actual_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"),
            bytes.fromhex(salt_hex), int(iterations)
        ).hex()
        return hmac.compare_digest(actual_hash, expected_hash)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int, token_version: int = 0) -> str:
    payload = {
        "user_id": user_id,
        "token_version": token_version,
        "expires_at": int(time.time()) + TOKEN_LIFETIME_SECONDS,
    }
    encoded_payload = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).decode("ascii").rstrip("=")
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return f"{encoded_payload}.{encoded_signature}"


def read_access_token(token: str) -> tuple[int, int]:
    try:
        encoded_payload, encoded_signature = token.split(".")
        expected_signature = hmac.new(
            SECRET_KEY.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256
        ).digest()
        supplied_signature = base64.urlsafe_b64decode(
            encoded_signature + "=" * (-len(encoded_signature) % 4)
        )
        if not hmac.compare_digest(expected_signature, supplied_signature):
            raise ValueError("Invalid token signature")
        payload = json.loads(
            base64.urlsafe_b64decode(
                encoded_payload + "=" * (-len(encoded_payload) % 4)
            )
        )
        if int(payload["expires_at"]) <= int(time.time()):
            raise ValueError("Token expired")
        return int(payload["user_id"]), int(payload.get("token_version", 0))
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid atau sudah kedaluwarsa.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Login JejakKBM menggunakan JSON, sedangkan akses endpoint memakai Bearer token.
# HTTPBearer membuat Swagger menampilkan kolom token biasa, bukan form OAuth2 password.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token login diperlukan.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id, token_version = read_access_token(credentials.credentials)
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active or user.token_version != token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Akun tidak ditemukan atau tidak aktif.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_roles(*allowed_roles: str):
    def check_role(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Akun tidak memiliki izin untuk melakukan tindakan ini.",
            )
        return user
    return check_role
