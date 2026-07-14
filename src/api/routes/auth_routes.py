# Login + current-user routes. Why this file exists: it's the one place that turns a
# Google identity into our own session — everything downstream (items_routes.py, any
# new route you add) only ever deals with our JWT via get_current_user, never Google's
# token directly.

import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.middleware.auth import get_current_user
from src.services.auth_service import GoogleTokenError, create_access_token, verify_google_id_token
from src.services.background_tasks import log_login_event
from src.store.user_store import UserStore

router = APIRouter()
user_store = UserStore()


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(description="Google ID token obtained client-side via @react-oauth/google")


@router.post("/google")
async def login_with_google(body: GoogleLoginRequest, background_tasks: BackgroundTasks):
    """Exchange a Google ID token for our own session JWT.

    Called once per login (not per request) — the frontend gets this token's id_token
    from Google directly in the browser, sends it here, and stores whatever we return.
    """
    try:
        # verify_google_id_token is a blocking call (google-auth does a synchronous
        # HTTP request under the hood to fetch/validate against Google's public keys).
        # asyncio.to_thread runs it on a worker thread instead of the event loop, so
        # this one slow network call doesn't stall every other concurrent request this
        # process is handling.
        claims = await asyncio.to_thread(verify_google_id_token, body.id_token)
    except GoogleTokenError as e:
        raise HTTPException(status_code=401, detail=str(e))

    # Upsert, not insert: same google_sub logging in again updates their profile fields
    # (name/picture may have changed) instead of erroring on the unique constraint.
    user = await user_store.upsert_from_google(
        google_sub=claims["sub"],
        email=claims["email"],
        name=claims.get("name"),
        picture=claims.get("picture"),
    )
    access_token = create_access_token(user_id=str(user.id), email=user.email)

    # Logging the login shouldn't delay the response — scheduled to run after this
    # function returns (see src/services/background_tasks.py for what this is/isn't).
    background_tasks.add_task(log_login_event, user_id=str(user.id), email=user.email)

    return {
        "status": "success",
        "data": {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user.to_dict(),
        },
    }


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    """Returns the caller's own profile. Used by the frontend on page load to confirm
    the stored JWT is still valid and to get a display name/email for the UI."""
    user = await user_store.get_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "success", "data": user.to_dict()}
