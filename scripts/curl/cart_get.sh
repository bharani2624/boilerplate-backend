#!/usr/bin/env bash
# Usage: TOKEN=... ./scripts/curl/cart_get.sh
set -euo pipefail
BASE="${API_BASE:-http://localhost:8000}"
curl -sS -H "Authorization: Bearer ${TOKEN}" "${BASE}/api/cart" | python3 -m json.tool
