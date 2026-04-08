#!/usr/bin/env bash
set -euo pipefail

SSM_PREFIX="arn:aws:ssm:${AWS_REGION}:${AWS_ACCOUNT_ID}:parameter/copilot/${ECS_APP_NAME}/${ENV}/secrets"

SECRETS=$(yq -r '.secrets[]' manifest.yml | jq -R -s -c '
  split("\n") | map(select(length > 0)) | map({
    name: .,
    valueFrom: ("'"$SSM_PREFIX"'/" + .)
  })
')

jq --argjson secrets "$SECRETS" \
  '.containerDefinitions[0].secrets = $secrets' \
  task-definition.json > task-definition-updated.json

mv task-definition-updated.json task-definition.json
