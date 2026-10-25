#!/bin/sh
set -e
if [ -z "$JWT_SECRET" ] || [ "$JWT_SECRET" = "change-me-to-a-long-random-string" ]; then
  echo "JWT_SECRET must be a unique secret" >&2
  exit 1
fi
awk -v s="$JWT_SECRET" '{gsub(/__JWT_SECRET__/, s); print}' /kong/kong.yml > /tmp/kong.yml
export KONG_DECLARATIVE_CONFIG=/tmp/kong.yml
exec /docker-entrypoint.sh kong docker-start
