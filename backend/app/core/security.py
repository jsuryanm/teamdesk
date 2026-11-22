from datetime import UTC, datetime, timedelta 

import jwt 
from pwdlib import PasswordHash
 

from backend.app.core.config import Settings


_hasher = PasswordHash.recommended()
# Scrambles a readable password into a string of random characters it can't be reversed

DUMMY_HASH = _hasher.hash('not-a-real-password')

def hash_password(plain: str):
    """Hashes the password"""
    return _hasher.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    """Verifies the password and hashed password are the same"""
    return _hasher.verify(plain, hashed)

def create_access_token(
    user_id: int,
    settings: Settings
) -> tuple[str, int]:
    """Creates a JWT token for user password"""
    now = datetime.now()
    expires = timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + expires,
        "type": "access"
    }

    token = jwt.encode(
        payload=payload,
        key=settings.secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm
    )
    # takes a secret password and turns it into a compact tamper proof string called JSON web token

    return token, int(expires.total_seconds())

def decode_access_token(
    token: str, 
    settings: Settings
) -> dict:
    """Raises jwt.InvalidTokenError if anything is wrong."""
    payload = jwt.decode(
        jwt=token,
        key=settings.secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
        options={'require':['exp','sub']}
    )
    # parses JWT string and extract readable payload

    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("wrong token type")
    return payload
