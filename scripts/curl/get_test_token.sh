#!/usr/bin/env bash
# Mint a session JWT without going through Google — upserts a test user directly
# against the database and prints a signed token, same shape as what
# POST /api/auth/google would return. Bypasses Google entirely, so it only exercises
# our own JWT/DB code, not the real OAuth path (use auth_google.sh for that).
#
# Must be run from the backend repo root with its Python env active (needs
# DATABASE_URL / JWT_SECRET_KEY — same values as whatever BASE_URL you're testing
# against, since the token is only valid against the database it was minted for).
#
# Usage: ./scripts/curl/get_test_token.sh test@example.com
set -euo pipefail

EMAIL="${1:?Usage: get_test_token.sh <email>}"
GOOGLE_SUB="test-sub-$(echo -n "$EMAIL" | shasum | cut -c1-16)"

python3 -c "
import asyncio
from src.store.user_store import UserStore
from src.services.auth_service import create_access_token

async def main():
    user = await UserStore().upsert_from_google('$GOOGLE_SUB', '$EMAIL', 'Test User', None)
    print(create_access_token(str(user.id), user.email))

asyncio.run(main())
"
