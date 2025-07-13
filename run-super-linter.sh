#!/bin/bash

# Helper script to run Super-Linter locally
# Usage: ./run-super-linter.sh [--all]

set -euo pipefail

VALIDATE_ALL_CODEBASE=${1:-false}

if [ "${1:-}" = "--all" ]; then
    VALIDATE_ALL_CODEBASE=true
    echo "🔍 Running Super-Linter on all files..."
else
    VALIDATE_ALL_CODEBASE=false
    echo "🔍 Running Super-Linter on changed files only..."
fi

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is required to run Super-Linter locally"
    echo "   Please install Docker and try again"
    exit 1
fi

# Pull the latest Super-Linter image
echo "📦 Pulling Super-Linter image..."
docker pull ghcr.io/super-linter/super-linter:v5.7.2

echo "🚀 Running Super-Linter..."
docker run --rm \
    -e DEFAULT_BRANCH=main \
    -e RUN_LOCAL=true \
    -e VALIDATE_ALL_CODEBASE="$VALIDATE_ALL_CODEBASE" \
    -e VALIDATE_YAML=true \
    -e VALIDATE_DOCKERFILE_HADOLINT=true \
    -e VALIDATE_BASH=true \
    -e VALIDATE_SHELL_SHFMT=true \
    -e VALIDATE_MARKDOWN=true \
    -e VALIDATE_ANSIBLE=true \
    -e VALIDATE_PYTHON_BLACK=true \
    -e VALIDATE_PYTHON_FLAKE8=true \
    -e VALIDATE_JSON=true \
    -e VALIDATE_KUBERNETES_KUBECONFORM=false \
    -e VALIDATE_CHECKOV=false \
    -e VALIDATE_TERRAFORM_TERRASCAN=false \
    -e VALIDATE_CSS=false \
    -e VALIDATE_JAVASCRIPT_ES=false \
    -e VALIDATE_TYPESCRIPT_ES=false \
    -e YAML_CONFIG_FILE=Script/.yamllint.yml \
    -e MARKDOWN_CONFIG_FILE=.markdownlint.yml \
    -e LOG_LEVEL=INFO \
    -e SUPPRESS_POSSUM=true \
    -v "$PWD":/tmp/lint \
    ghcr.io/super-linter/super-linter:v5.7.2

echo "✅ Super-Linter completed!"
