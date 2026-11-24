"""Password hashing (scrypt) and the static account list.

Hash format: scrypt:<salt hex>:<hash hex>. Generate one with `python -m app.hashpw`.
The format avoids "$" so it survives docker compose .env interpolation.
"""
import hashlib
import hmac
import secrets

from fastapi import HTTPException, Request

N, R, P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=N, r=R, p=P)
    return f"scrypt:{salt.hex()}:{digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_hex, hash_hex = stored.split(":")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=N, r=R, p=P)
    return hmac.compare_digest(digest.hex(), hash_hex)


def authenticate(settings, username: str, password: str) -> dict | None:
    # Static accounts for now; only the admin exists.
    if hmac.compare_digest(username, settings.admin_username) and verify_password(
        password, settings.admin_password_hash
    ):
        return {"username": settings.admin_username, "role": "admin"}
    return None


def current_user(request: Request) -> dict:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in")
    return user
