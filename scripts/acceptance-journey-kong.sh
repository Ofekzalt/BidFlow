#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KONG="${KONG_BASE_URL:-http://localhost:8080}"
PASS="${ACCEPTANCE_PASSWORD:-AcceptTest123!}"
TS="$(date +%s)"
SELLER_EMAIL="seller-${TS}@example.com"
BIDDER_EMAIL="bidder-${TS}@example.com"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

pass() {
  echo "PASS: $*"
}

json_field() {
  python3 -c 'import json,sys; print(json.load(sys.stdin)[sys.argv[1]])' "$1"
}

login() {
  local email="$1"
  curl -sf -X POST "${KONG}/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${email}\",\"password\":\"${PASS}\"}" \
    | json_field access_token
}

confirm_setup_intent() {
  local client_secret="$1"
  docker compose -f "${ROOT}/docker-compose.yml" exec -T settlement uv run python - <<PY
import os
import stripe

secret = """${client_secret}"""
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
seti_id = secret.split("_secret_")[0]
pm = stripe.PaymentMethod.create(type="card", card={"token": "tok_visa"})
stripe.SetupIntent.confirm(seti_id, payment_method=pm.id)
print(pm.id)
PY
}

wait_for_payment_method() {
  local token="$1"
  local label="$2"
  for _ in $(seq 1 30); do
    local count
    count="$(curl -sf "${KONG}/payments/methods" \
      -H "Authorization: Bearer ${token}" \
      | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')"
    if [[ "${count}" -ge 1 ]]; then
      pass "${label} payment method ready"
      return 0
    fi
    sleep 2
  done
  fail "${label} payment method not ready after polling"
}

setup_payment() {
  local token="$1"
  local label="$2"
  local client_secret
  client_secret="$(curl -sf -X POST "${KONG}/payments/setup-intent" \
    -H "Authorization: Bearer ${token}" \
    | json_field client_secret)"
  confirm_setup_intent "${client_secret}" >/dev/null
  wait_for_payment_method "${token}" "${label}"
}

iso_in_minutes() {
  local minutes="$1"
  python3 -c 'from datetime import datetime, timedelta, timezone; print((datetime.now(timezone.utc)+timedelta(minutes='"${minutes}"')).strftime("%Y-%m-%dT%H:%M:%S+00:00"))'
}

if [[ ! -f "${ROOT}/.stripe-listen.pid" ]] || ! kill -0 "$(cat "${ROOT}/.stripe-listen.pid")" 2>/dev/null; then
  echo "Starting Stripe webhook listener..."
  bash "${ROOT}/scripts/setup-stripe-webhook-local.sh"
  docker compose -f "${ROOT}/docker-compose.yml" up -d --force-recreate \
    settlement settlement-outbox-worker settlement-auction-ended-consumer
  for _ in $(seq 1 60); do
    hs="$(docker inspect bidflow-settlement-1 --format '{{.State.Health.Status}}' 2>/dev/null || echo starting)"
    if [[ "${hs}" == "healthy" ]]; then
      break
    fi
    sleep 5
  done
  for _ in $(seq 1 30); do
    curl -sf "${KONG}/auctions" >/dev/null 2>&1 && break
    sleep 2
  done
fi

echo "=== Register seller and bidder ==="
curl -sf -X POST "${KONG}/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${SELLER_EMAIL}\",\"password\":\"${PASS}\"}" >/dev/null
curl -sf -X POST "${KONG}/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${BIDDER_EMAIL}\",\"password\":\"${PASS}\"}" >/dev/null
pass "registered seller and bidder"

SELLER_TOKEN="$(login "${SELLER_EMAIL}")"
BIDDER_TOKEN="$(login "${BIDDER_EMAIL}")"
pass "logged in seller and bidder"

echo "=== Unauthenticated bid blocked ==="
AUCTION_ID_FOR_AUTH_TEST="$(curl -sf "${KONG}/auctions" | python3 -c 'import json,sys; data=json.load(sys.stdin); print(data[0]["id"] if data else "")')"
if [[ -n "${AUCTION_ID_FOR_AUTH_TEST}" ]]; then
  code="$(curl -s -o /dev/null -w "%{http_code}" -X POST "${KONG}/auctions/${AUCTION_ID_FOR_AUTH_TEST}/bids" \
    -H "Content-Type: application/json" \
    -H "Idempotency-Key: $(uuidgen)" \
    -d '{"amount_cents":999999}')"
  [[ "${code}" == "401" ]] || fail "expected 401 for unauthenticated bid, got ${code}"
  pass "unauthenticated bid returns 401"
fi

echo "=== Payment setup ==="
setup_payment "${SELLER_TOKEN}" "seller"
setup_payment "${BIDDER_TOKEN}" "bidder"

echo "=== Create and open auction ==="
START_TIME="$(iso_in_minutes 0)"
END_TIME="$(iso_in_minutes 3)"
AUCTION_JSON="$(curl -sf -X POST "${KONG}/auctions" \
  -H "Authorization: Bearer ${SELLER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"Acceptance ${TS}\",\"description\":\"Step 12 journey\",\"starting_price_cents\":1000,\"start_time\":\"${START_TIME}\",\"end_time\":\"${END_TIME}\"}")"
AUCTION_ID="$(echo "${AUCTION_JSON}" | json_field id)"
curl -sf -X POST "${KONG}/auctions/${AUCTION_ID}/open" \
  -H "Authorization: Bearer ${SELLER_TOKEN}" >/dev/null
STATUS="$(curl -sf "${KONG}/auctions/${AUCTION_ID}" | json_field status)"
[[ "${STATUS}" == "OPEN" ]] || fail "expected OPEN, got ${STATUS}"
pass "auction ${AUCTION_ID} is OPEN until ${END_TIME}"

echo "=== Seller cannot bid on own auction (UI hides form; API should reject) ==="
seller_bid_code="$(curl -s -o /dev/null -w "%{http_code}" -X POST "${KONG}/auctions/${AUCTION_ID}/bids" \
  -H "Authorization: Bearer ${SELLER_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"amount_cents":1100}')"
[[ "${seller_bid_code}" == "403" ]] || fail "expected 403 for seller self-bid, got ${seller_bid_code}"
pass "seller self-bid returns 403"

echo "=== Place winning bid ==="
curl -sf -X POST "${KONG}/auctions/${AUCTION_ID}/bids" \
  -H "Authorization: Bearer ${BIDDER_TOKEN}" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"amount_cents":1100}' >/dev/null
CURRENT="$(curl -sf "${KONG}/auctions/${AUCTION_ID}" | python3 -c 'import json,sys; a=json.load(sys.stdin); print(a["current_price_cents"])')"
[[ "${CURRENT}" == "1100" ]] || fail "expected current price 1100, got ${CURRENT}"
pass "bid accepted, current price ${CURRENT}"

echo "=== Wait for close and settlement ==="
FINAL_STATUS=""
for _ in $(seq 1 120); do
  FINAL_STATUS="$(curl -sf "${KONG}/auctions/${AUCTION_ID}" | json_field status)"
  if [[ "${FINAL_STATUS}" == "SOLD" || "${FINAL_STATUS}" == "UNPAID" || "${FINAL_STATUS}" == "UNSOLD" ]]; then
    break
  fi
  sleep 2
done
[[ "${FINAL_STATUS}" == "SOLD" || "${FINAL_STATUS}" == "UNPAID" ]] \
  || fail "expected SOLD or UNPAID, got ${FINAL_STATUS}"
pass "auction closed with status ${FINAL_STATUS}"

echo "=== Notifications ==="
NOTIF_TYPES="$(curl -sf "${KONG}/notifications" \
  -H "Authorization: Bearer ${BIDDER_TOKEN}" \
  | python3 -c 'import json,sys; print(",".join(n["type"] for n in json.load(sys.stdin)))')"
[[ "${NOTIF_TYPES}" == *Payment* ]] || fail "expected payment notification, got: ${NOTIF_TYPES}"
pass "bidder notifications include payment outcome (${NOTIF_TYPES})"

echo ""
echo "Acceptance journey complete."
echo "Seller: ${SELLER_EMAIL}"
echo "Bidder: ${BIDDER_EMAIL}"
echo "Auction: ${AUCTION_ID}"
echo "Final status: ${FINAL_STATUS}"
echo "Frontend: http://localhost:5173/auctions/${AUCTION_ID}"
