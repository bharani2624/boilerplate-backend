"""Google ID token verification and our own session JWT issuance.

Flow:
1. Frontend uses @react-oauth/google to get a Google ID token (client-side, no secret needed).
2. Frontend POSTs that id_token to POST /api/auth/google.
3. Backend verifies the id_token against Google's public keys (verify_google_id_token),
   upserts a User row keyed on the stable Google "sub" claim, and mints our own JWT
   (create_access_token) containing {sub: user_id, email}.
4. Frontend sends that JWT as `Authorization: Bearer <token>` on every subsequent request.
   Verification (decode_access_token) is stateless — no server-side session store — so it
   scales to any number of concurrent users without extra infra.
"""

from datetime import datetime, timedelta
from typing import Optional

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from jose import JWTError, jwt

from config.settings import settings


class GoogleTokenError(Exception):
    """Raised whenever a Google ID token fails verification — caught in auth_routes.py
    and turned into a 401 so the caller sees a clean error instead of a 500."""
    pass


def verify_google_id_token(token: str) -> dict:
    """Verify a Google ID token and return its claims (sub, email, name, picture).

    google-auth checks the token's signature against Google's public keys, its
    expiry, and that it was issued for our GOOGLE_CLIENT_ID (so a token minted for a
    different app's OAuth client can't be replayed against this API). We additionally
    check `iss` ourselves as defense in depth.
    """
    if not settings.google_client_id:
        raise GoogleTokenError("GOOGLE_CLIENT_ID is not configured on the server")
    try:
        claims = google_id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.google_client_id
        )
    except ValueError as e:
        raise GoogleTokenError(str(e))

    if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise GoogleTokenError("Invalid token issuer")

    return claims


def create_access_token(user_id: str, email: str) -> str:
    """Mint our own JWT after a successful Google login. This is what the frontend
    actually stores and sends back on every request — Google's token is only used
    once, at login, to prove identity."""
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expiry_minutes)
    payload = {"sub": str(user_id), "email": email, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[dict]:
    """Verify + decode our own JWT. Returns None on any failure (expired, bad
    signature, malformed) rather than raising, so callers (get_current_user) can
    turn any failure into the same 401 without a try/except of their own."""
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
