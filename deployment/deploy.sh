#!/bin/bash
# Deployment script that GitHub Actions will run via SSH
# This script pulls the latest Docker images and restarts services

set -e

# Configuration
PROJECT_DIR="/home/github-deploy/osce-project"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.yml"
GITHUB_REGISTRY="ghcr.io"
GITHUB_REPO="${GITHUB_REPOSITORY:-madgaa-lab/osce-project}"  # Will be passed from GitHub Actions

echo "=== Starting deployment ==="
echo "Repository: ${GITHUB_REPO}"
echo "Project directory: ${PROJECT_DIR}"

# Create project directory if it doesn't exist
mkdir -p "${PROJECT_DIR}"

# Check required environment variables
if [ -z "$API_KEY" ]; then
    echo "ERROR: API_KEY environment variable is not set"
    exit 1
fi

# Download docker-compose.yml from repository
echo ""
echo "=== Downloading docker-compose.yml ==="
BRANCH="${GITHUB_REF_NAME:-main}"
curl -fsSL "https://raw.githubusercontent.com/${GITHUB_REPO}/${BRANCH}/deployment/docker-compose.yml" -o "${COMPOSE_FILE}"

# Pull latest images
echo ""
echo "=== Pulling latest Docker images ==="
docker pull "${GITHUB_REGISTRY}/${GITHUB_REPO}-medical-judge:latest"
docker pull "${GITHUB_REGISTRY}/${GITHUB_REPO}-doctor-agent:latest"

# Stop and remove old containers
echo ""
echo "=== Stopping old containers ==="
cd "${PROJECT_DIR}"
if [ -f "${COMPOSE_FILE}" ]; then
    docker compose down || docker-compose down || true
fi

# Start new containers
echo ""
echo "=== Starting new containers ==="
docker compose up -d || docker-compose up -d

# Show running containers
echo ""
echo "=== Running containers ==="
docker ps

# Cleanup old images
echo ""
echo "=== Cleaning up old images ==="
docker image prune -f

echo ""
echo "=== Deployment complete ==="
