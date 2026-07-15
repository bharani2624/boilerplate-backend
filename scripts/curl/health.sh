#!/usr/bin/env bash
# GET /api/health — unauthenticated liveness check.
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

curl -s -w "\nHTTP %{http_code}\n" "$BASE_URL/api/health"
