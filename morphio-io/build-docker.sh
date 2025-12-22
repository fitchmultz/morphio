#!/bin/bash

set -euo pipefail

# Set variables
GITHUB_USERNAME="fitchmultz"
BACKEND_IMAGE_NAME="morphio-io-backend"
FRONTEND_IMAGE_NAME="morphio-io-frontend"
TAG="latest"
PORTAINER_WEBHOOK_URL_MORPHIO="${PORTAINER_WEBHOOK_URL_MORPHIO}"

# Function to show elapsed time
show_elapsed_time() {
  local start_time=$1
  local end_time=$(date +%s)
  local elapsed=$((end_time - start_time))
  echo "Elapsed time: $elapsed seconds"
}

# Function to build and push image with timing
build_and_push() {
  local dockerfile=$1
  local image_name=$2
  local build_args=$3
  local start_time=$(date +%s)
  local dockerfile_dir=$(dirname $dockerfile)

  # Create temporary .dockerignore if it doesn't exist
  if [ ! -f "${dockerfile_dir}/.dockerignore" ]; then
    touch "${dockerfile_dir}/.dockerignore"
  fi

  # Ensure proper line endings in .dockerignore
  if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sed -i'' -e 's/\r$//' "${dockerfile_dir}/.dockerignore"
  fi

  echo "Starting build for $image_name..."
  echo "Contents of .dockerignore:"
  cat "${dockerfile_dir}/.dockerignore"

  # Use --no-cache option if you want to force a fresh build
  DOCKER_BUILDKIT=1 docker buildx build \
    --platform linux/amd64 \
    -t ghcr.io/$GITHUB_USERNAME/$image_name:$TAG \
    -f $dockerfile \
    $build_args \
    --push \
    --cache-from type=registry,ref=ghcr.io/$GITHUB_USERNAME/$image_name:cache \
    --cache-to type=registry,ref=ghcr.io/$GITHUB_USERNAME/$image_name:cache,mode=max \
    --progress=plain \
    .

  local status=$?
  show_elapsed_time $start_time

  if [ $status -ne 0 ]; then
    echo "Error: Failed to build and push $image_name"
    exit 1
  fi
}

# Login to GitHub Container Registry
echo "Logging into GitHub Container Registry..."
echo $GHCR_PAT | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin

# Build and push images
build_and_push "./backend/Dockerfile" $BACKEND_IMAGE_NAME "--build-arg ENVIRONMENT=production"
build_and_push "./frontend/Dockerfile" $FRONTEND_IMAGE_NAME ""

# Trigger Portainer webhook
echo "Triggering Portainer webhook..."
WEBHOOK_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST $PORTAINER_WEBHOOK_URL_MORPHIO)

if [ "$WEBHOOK_RESPONSE" -eq 200 ]; then
  echo "Portainer webhook triggered successfully."
else
  echo "Failed to trigger Portainer webhook. HTTP status code: $WEBHOOK_RESPONSE"
fi

# Cleanup
docker logout ghcr.io
