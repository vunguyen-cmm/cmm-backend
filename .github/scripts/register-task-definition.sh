#!/usr/bin/env bash
set -euo pipefail

TASK_DEF_ARN=$(aws ecs register-task-definition \
  --cli-input-json "file://$TASK_DEF_FILE" \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)

echo "task-def-arn=$TASK_DEF_ARN" >> "$GITHUB_OUTPUT"
