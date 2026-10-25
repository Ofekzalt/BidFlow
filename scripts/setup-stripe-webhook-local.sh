#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SETTLEMENT_ENV_FILE="${ROOT}/settlement/.env"
ROOT_ENV_FILE="${ROOT}/.env"
FORWARD_URL="${STRIPE_WEBHOOK_FORWARD_URL:-http://localhost:8080/webhooks/stripe}"
LOG_FILE="${ROOT}/.stripe-listen.log"
PID_FILE="${ROOT}/.stripe-listen.pid"

if [[ ! -f "${SETTLEMENT_ENV_FILE}" ]]; then
  echo "Missing ${SETTLEMENT_ENV_FILE}. Copy settlement/.env.example first." >&2
  exit 1
fi

STRIPE_SECRET_KEY="$(grep '^STRIPE_SECRET_KEY=' "${SETTLEMENT_ENV_FILE}" | cut -d= -f2-)"
if [[ -z "${STRIPE_SECRET_KEY}" || "${STRIPE_SECRET_KEY}" == *placeholder* ]]; then
  echo "Set a real STRIPE_SECRET_KEY in ${SETTLEMENT_ENV_FILE} first." >&2
  exit 1
fi

if ! command -v stripe >/dev/null 2>&1; then
  echo "Stripe CLI not found. Install with: brew install stripe/stripe-cli/stripe" >&2
  exit 1
fi

WEBHOOK_SECRET="$(
  stripe listen \
    --forward-to "${FORWARD_URL}" \
    --api-key "${STRIPE_SECRET_KEY}" \
    --print-secret
)"

if [[ -z "${WEBHOOK_SECRET}" || "${WEBHOOK_SECRET}" != whsec_* ]]; then
  echo "Failed to obtain a webhook signing secret from Stripe CLI." >&2
  exit 1
fi

patch_env_value() {
  local file="$1"
  local key="$2"
  local value="$3"
  if [[ ! -f "${file}" ]]; then
    return
  fi
  if grep -q "^${key}=" "${file}"; then
    sed -i '' "s|^${key}=.*|${key}=${value}|" "${file}"
  else
    printf '\n%s=%s\n' "${key}" "${value}" >>"${file}"
  fi
}

patch_env_value "${SETTLEMENT_ENV_FILE}" "STRIPE_WEBHOOK_SECRET" "${WEBHOOK_SECRET}"
patch_env_value "${ROOT_ENV_FILE}" "STRIPE_WEBHOOK_SECRET" "${WEBHOOK_SECRET}"
patch_env_value "${ROOT_ENV_FILE}" "STRIPE_SECRET_KEY" "${STRIPE_SECRET_KEY}"

if [[ -f "${PID_FILE}" ]]; then
  OLD_PID="$(cat "${PID_FILE}")"
  if kill -0 "${OLD_PID}" 2>/dev/null; then
    kill "${OLD_PID}" 2>/dev/null || true
    sleep 1
  fi
  rm -f "${PID_FILE}"
fi

nohup stripe listen \
  --forward-to "${FORWARD_URL}" \
  --api-key "${STRIPE_SECRET_KEY}" \
  </dev/null >>"${LOG_FILE}" 2>&1 &
LISTENER_PID=$!
disown "${LISTENER_PID}" 2>/dev/null || true
echo "${LISTENER_PID}" >"${PID_FILE}"

echo "Updated STRIPE_WEBHOOK_SECRET in settlement/.env"
if [[ -f "${ROOT_ENV_FILE}" ]]; then
  echo "Updated STRIPE_WEBHOOK_SECRET and STRIPE_SECRET_KEY in .env"
fi
echo "Stripe listener running (pid $(cat "${PID_FILE}")) forwarding to ${FORWARD_URL}"
echo "Logs: ${LOG_FILE}"
echo "Stop with: kill \$(cat ${PID_FILE})"
echo "Recreate settlement services: docker compose up -d --force-recreate settlement settlement-outbox-worker settlement-auction-ended-consumer"
