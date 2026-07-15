#!/usr/bin/env bash
# GET /api/auth/me — returns the current user for the given $TOKEN.
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
TOKEN="${TOKEN:?Set TOKEN (see README.md — get_test_token.sh or auth_google.sh)}"

curl -s -w "\nHTTP %{http_code}\n" "$BASE_URL/api/auth/me" \
  -H "Authorization: Bearer $TOKEN"
