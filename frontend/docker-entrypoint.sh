#!/bin/sh
set -eu

: "${BACKEND_URL:=}"
: "${BACKEND_PORT:=8000}"

envsubst '${BACKEND_URL} ${BACKEND_PORT}' < /usr/share/nginx/html/env.template.js > /usr/share/nginx/html/env.js

exec "$@"
