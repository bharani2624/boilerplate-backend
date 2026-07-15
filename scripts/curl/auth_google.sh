#!/usr/bin/env bash
# POST /api/auth/google — exchange a real Google ID token for our session JWT.
# Get an id_token from the frontend: open devtools on /login, look at the request
# body of the POST /api/auth/google call after clicking "Sign in with Google".
#
# Usage: ./scripts/curl/auth_google.sh "<id_token>"
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
ID_TOKEN="${1:?Usage: auth_google.sh <id_token>}"

curl -s -w "\nHTTP %{http_code}\n" -X POST "$BASE_URL/api/auth/google" \
  -H "Content-Type: application/json" \
  -d "{\"id_token\": \"$ID_TOKEN\"}"
