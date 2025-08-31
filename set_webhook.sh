#!/usr/bin/env bash
# Uso:
#   export TELEGRAM_TOKEN=xxxx:yyyy
#   export PUBLIC_URL=https://seu-servico.onrender.com
#   export WEBHOOK_SECRET=um_segredo_curto
#   ./set_webhook.sh

set -euo pipefail
: "${TELEGRAM_TOKEN:?Precisa TELEGRAM_TOKEN no ambiente}"
: "${PUBLIC_URL:?Precisa PUBLIC_URL no ambiente}"
: "${WEBHOOK_SECRET:?Precisa WEBHOOK_SECRET no ambiente}"

curl -sS -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/setWebhook"   -d "url=${PUBLIC_URL}/webhook/${TELEGRAM_TOKEN}"   -d "secret_token=${WEBHOOK_SECRET}" | jq .
