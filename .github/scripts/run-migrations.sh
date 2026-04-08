#!/usr/bin/env bash
set -euo pipefail

NETWORK_CONFIG=$(aws ecs describe-services \
  --cluster "cmm-$ENV-cluster" \
  --services "cmm-$ENV-backend" \
  --query 'services[0].networkConfiguration' \
  --output json)

TASK_ARN=$(aws ecs run-task \
  --cluster "cmm-$ENV-cluster" \
  --task-definition "$TASK_DEF_ARN" \
  --launch-type FARGATE \
  --network-configuration "$NETWORK_CONFIG" \
  --overrides '{"containerOverrides":[{"name":"backend","command":["alembic","upgrade","head"]}]}' \
  --query 'tasks[0].taskArn' \
  --output text)

echo "Waiting for migration task $TASK_ARN to complete..."
aws ecs wait tasks-stopped --cluster "cmm-$ENV-cluster" --tasks "$TASK_ARN"

EXIT_CODE=$(aws ecs describe-tasks \
  --cluster "cmm-$ENV-cluster" \
  --tasks "$TASK_ARN" \
  --query 'tasks[0].containers[0].exitCode' \
  --output text)

if [[ "$EXIT_CODE" != "0" ]]; then
  echo "Migration task failed with exit code $EXIT_CODE"
  exit 1
fi

echo "Migrations completed successfully"
