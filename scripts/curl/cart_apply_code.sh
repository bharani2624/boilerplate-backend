#!/usr/bin/env bash
# Usage: TOKEN=... CODE=SAVE10 ./scripts/curl/cart_apply_code.sh
set -euo pipefail
BASE="${API_BASE:-http://localhost:8000}"
CODE="${CODE:-SAVE10}"
curl -sS -X POST -H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" \
  -d "{\"code\":\"${CODE}\"}" \
  "${BASE}/api/cart/apply-code" | python3 -m json.tool
