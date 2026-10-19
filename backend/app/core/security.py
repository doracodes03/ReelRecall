import base64
import hashlib
import hmac
import json
import secrets
import time

from fastapi import HTTPException, status

from app.core.config import settings

_PBKDF2_ITERATIONS = 310_000
_TOKEN_ISSUER = "reelrecall"


def _secret() -> bytes:
    secret = settings.jwt_secret.encode("utf-8")
    if len(secret) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured. Set JWT_SECRET to at least 32 characters.",
        )
    return secret


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS
    )
    return "$".join(
        (
            "pbkdf2_sha256",
            str(_PBKDF2_ITERATIONS),
            base64.urlsafe_b64encode(salt).decode("ascii").rstrip("="),
            base64.urlsafe_b64encode(digest).decode("ascii").rstrip("="),
        )
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        if not 100_000 <= iterations <= 2_000_000:
            return False
        salt = base64.urlsafe_b64decode(salt_text + "=" * (-len(salt_text) % 4))
        expected = base64.urlsafe_b64decode(
            digest_text + "=" * (-len(digest_text) % 4)
        )
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(actual, expected)


def create_access_token(user_id: str) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": _TOKEN_ISSUER,
        "sub": user_id,
        "iat": now,
        "exp": now + settings.access_token_expire_minutes * 60,
    }
    encode = lambda value: base64.urlsafe_b64encode(
        json.dumps(value, separators=(",", ":")).encode("utf-8")
    ).decode("ascii").rstrip("=")
    signed = f"{encode(header)}.{encode(payload)}"
    signature = hmac.new(_secret(), signed.encode("ascii"), hashlib.sha256).digest()
    return f"{signed}.{base64.urlsafe_b64encode(signature).decode('ascii').rstrip('=')}"


def decode_access_token(token: str) -> str:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        header_text, payload_text, signature_text = token.split(".")
        signed = f"{header_text}.{payload_text}"
        signature = base64.urlsafe_b64decode(
            signature_text + "=" * (-len(signature_text) % 4)
        )
        expected = hmac.new(_secret(), signed.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise unauthorized
        header = json.loads(
            base64.urlsafe_b64decode(header_text + "=" * (-len(header_text) % 4))
        )
        payload = json.loads(
            base64.urlsafe_b64decode(payload_text + "=" * (-len(payload_text) % 4))
        )
        if (
            header.get("alg") != "HS256"
            or payload.get("iss") != _TOKEN_ISSUER
            or not isinstance(payload.get("sub"), str)
            or not payload["sub"]
            or not isinstance(payload.get("exp"), int)
            or payload["exp"] <= int(time.time())
        ):
            raise unauthorized
        return payload["sub"]
    except HTTPException:
        raise
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise unauthorized from exc
