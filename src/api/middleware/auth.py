"""FastAPI dependency that authenticates a request via `Authorization: Bearer <jwt>`.

Why this file exists: rather than every route re-parsing headers and decoding JWTs,
routes just add `current_user: dict = Depends(get_current_user)` as a parameter and
FastAPI runs this before the route body — so an invalid/missing token never reaches
route code at all.
"""

from fastapi import Header, HTTPException, status

from src.services.auth_service import decode_access_token


async def get_current_user(authorization: str = Header(default=None)) -> dict:
    """Returns {"user_id": ..., "email": ...} or raises 401.

    user_id here is our own User.id (the row created in upsert_from_google), not
    Google's sub — it's what stores use to scope queries to "this user's data only"
    (see item_store.py, which takes user_id on every method).
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    return {"user_id": payload["sub"], "email": payload["email"]}
