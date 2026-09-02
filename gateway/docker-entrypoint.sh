#!/bin/sh
set -e
awk -v s="$JWT_SECRET" '{gsub(/__JWT_SECRET__/, s); print}' /kong/kong.yml > /tmp/kong.yml
export KONG_DECLARATIVE_CONFIG=/tmp/kong.yml
exec /docker-entrypoint.sh kong docker-start
