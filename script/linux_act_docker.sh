#!/bin/bash

# Install Act (GitHub Actions locally) via Docker
# This script sets up Act to run GitHub Actions workflows locally using Docker

set -euo pipefail

echo "🚀 Installing Act for GitHub Actions local execution..."

# Function to ensure act Docker image exists
ensure_act_docker() {
    if ! docker images | grep -q "local/act"; then
        echo "Building act Docker image..."
        docker build -t local/act - <<DOCKERFILE
FROM golang:alpine
RUN apk add --no-cache git docker-cli
RUN go install github.com/nektos/act@latest
ENTRYPOINT ["/go/bin/act"]
DOCKERFILE
    else
        echo "Act Docker image already exists."
    fi
}

# Create act function in shell profile
setup_act_function() {
    local profile_file="$HOME/.bashrc"
    
    # Check if function already exists
    if grep -q "^act()" "$profile_file" 2>/dev/null; then
        echo "Act function already exists in $profile_file"
        return 0
    fi
    
    echo "Adding act function to $profile_file..."
    cat >> "$profile_file" << 'SHELL_FUNC'

# Act function for running GitHub Actions locally
act() {
    ensure_act_docker
    docker run --rm \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v "$PWD:$PWD" \
        -w "$PWD" \
        local/act "$@"
}

# Function to ensure act Docker image exists
ensure_act_docker() {
    if ! docker images | grep -q "local/act"; then
        echo "Building act Docker image..."
        docker build -t local/act - <<DOCKERFILE
FROM golang:alpine
RUN apk add --no-cache git docker-cli
RUN go install github.com/nektos/act@latest
ENTRYPOINT ["/go/bin/act"]
DOCKERFILE
    fi
}
SHELL_FUNC
}

main() {
    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        echo "❌ Error: Docker is not installed or not in PATH"
        echo "Please install Docker first: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        echo "❌ Error: Docker is not running"
        echo "Please start Docker and try again"
        exit 1
    fi
    
    # Build the act Docker image
    ensure_act_docker
    
    # Set up the shell function
    setup_act_function
    
    echo "✅ Act installation completed!"
    echo ""
    echo "To use act, either:"
    echo "  1. Source your profile: source ~/.bashrc"
    echo "  2. Open a new terminal"
    echo ""
    echo "Then you can run: act --list"
    echo ""
    echo "For the current session, you can also source the Act via Docker script:"
    echo "  source \"$(dirname "$0")/# Act via Docker.sh\""
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
