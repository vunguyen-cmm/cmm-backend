#!/usr/bin/env bash
set -euo pipefail

docker build \
  -t "$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" \
  -t "$ECR_REGISTRY/$ECR_REPOSITORY:$ENV-latest" \
  .

docker push "$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG"
docker push "$ECR_REGISTRY/$ECR_REPOSITORY:$ENV-latest"

echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> "$GITHUB_OUTPUT"
