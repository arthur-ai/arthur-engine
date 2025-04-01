#!/bin/bash

if [[ $GENAI_ENGINE_ENVIRONMENT == "local" ]]; then
  env
fi

echo "==> Validating environment variables"
for var in GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS POSTGRES_USER POSTGRES_PASSWORD POSTGRES_URL POSTGRES_PORT POSTGRES_DB GENAI_ENGINE_ADMIN_KEY; do
if [[ -z "${!var}" ]]; then
missing_vars+=" $var"
fi
done

if [[ -n "$missing_vars" ]]; then
echo "==> Missing required environment variable values: $missing_vars"
exit 1
fi

if [[ -n "${OPENAI_DNS_OVERRIDE_HOSTNAME}" && -n "${OPENAI_DNS_OVERRIDE_IP}" ]]; then
  echo "==> Overriding DNS for OpenAI"
  echo "$OPENAI_DNS_OVERRIDE_IP" "$OPENAI_DNS_OVERRIDE_HOSTNAME" | tee -a /etc/hosts && cat /etc/hosts
fi

if [[ -n "$POSTGRES_SSL_CERT_DOWNLOAD_URL" ]]; then
  echo "==> Downloading Postgres SSL cert"
  python3 -c "import urllib.request; urllib.request.urlretrieve('"${POSTGRES_SSL_CERT_DOWNLOAD_URL}"', 'postgres-cert.pem')"
  if [[ $? == 0 ]]; then
    echo "Postgres SSL cert downloaded with success"
  else
    echo "Error downloading Postgres SSL cert";
  fi
fi

if [[ -n "$KEYCLOAK_USE_PRIVATE_CERT" ]]; then
  echo "==> Downloading KeyCloak SSL cert from $KEYCLOAK_SSL_CERT_DOWNLOAD_URL"
  python3 -c "import urllib.request; urllib.request.urlretrieve('"${KEYCLOAK_SSL_CERT_DOWNLOAD_URL}"', 'postgres-cert.pem')"
  if [[ $? == 0 ]]; then
    echo "KeyCloak SSL cert downloaded with success"
  else
    echo "Error downloading KeyCloak SSL cert";
  fi
fi

export PYTHONPATH="src"

echo "==> Running database migration"
poetry run alembic upgrade head || exit 1

echo "==> Starting the GenAI Engine server with ${WORKER:-1} worker"
poetry run gunicorn src.server:get_app -c /app/src/gunicorn.conf.py --preload
