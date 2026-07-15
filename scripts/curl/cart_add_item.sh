#!/usr/bin/env bash
# Usage: TOKEN=... PRODUCT_ID=hoodie QTY=1 ./scripts/curl/cart_add_item.sh
set -euo pipefail
BASE="${API_BASE:-http://localhost:8000}"
PRODUCT_ID="${PRODUCT_ID:-hoodie}"
QTY="${QTY:-1}"
curl -sS -X POST -H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" \
  -d "{\"product_id\":\"${PRODUCT_ID}\",\"qty\":${QTY}}" \
  "${BASE}/api/cart/items" | python3 -m json.tool
