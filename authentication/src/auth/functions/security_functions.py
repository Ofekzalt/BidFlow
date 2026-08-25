from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from auth.config import settings
from auth.constants import (
    JWT_ALGORITHM,
    JWT_CLAIM_AUD,
    JWT_CLAIM_EMAIL,
    JWT_CLAIM_EXP,
    JWT_CLAIM_IAT,
    JWT_CLAIM_ISS,
    JWT_CLAIM_SUB,
)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(user_id: str, email: str) -> str:
    now = datetime.now(UTC)
    payload = {
        JWT_CLAIM_SUB: user_id,
        JWT_CLAIM_EMAIL: email,
        JWT_CLAIM_IAT: now,
        JWT_CLAIM_EXP: now + timedelta(seconds=settings.jwt_expires_seconds),
        JWT_CLAIM_ISS: settings.jwt_issuer,
        JWT_CLAIM_AUD: settings.jwt_audience,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)
