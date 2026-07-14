"""FastAPI dependency that authenticates a request via `Authorization: Bearer <jwt>`."""

from fastapi import Header, HTTPException, status

from src.services.auth_service import decode_access_token


async def get_current_user(authorization: str = Header(default=None)) -> dict:
    """Returns {"user_id": ..., "email": ...} or raises 401."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    return {"user_id": payload["sub"], "email": payload["email"]}
