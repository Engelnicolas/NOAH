#!/bin/bash

# Setup script for NOAH project linting and pre-commit hooks
# This script sets up the development environment with Super-Linter integration

set -euo pipefail

echo "🚀 Setting up NOAH development environment with Super-Linter"
echo "==========================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f ".pre-commit-config.yaml" ]; then
    print_error "This script must be run from the NOAH project root directory"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is required but not installed"
    exit 1
fi

# Check if Docker is available for Super-Linter
if ! command -v docker &> /dev/null; then
    print_warning "Docker is not available. Super-Linter will not work locally."
    print_warning "Install Docker to run Super-Linter locally."
fi

# Install pre-commit
print_status "Installing pre-commit..."
pip3 install --user pre-commit

# Verify pre-commit installation
if ! command -v pre-commit &> /dev/null; then
    print_warning "pre-commit not found in PATH. You may need to add ~/.local/bin to your PATH"
    export PATH="$HOME/.local/bin:$PATH"
fi

# Install pre-commit hooks
print_status "Installing pre-commit hooks..."
pre-commit install

# Install commit-msg hook for conventional commits (optional)
pre-commit install --hook-type commit-msg

# Update hooks to latest versions
print_status "Updating pre-commit hooks..."
pre-commit autoupdate

# Run hooks on all files to verify setup
print_status "Running initial validation on all files..."
if pre-commit run --all-files; then
    print_success "All pre-commit hooks passed!"
else
    print_warning "Some pre-commit hooks failed. This is normal for the initial setup."
    print_warning "Fix any issues and commit your changes."
fi

# Create a helper script for running Super-Linter manually
print_status "Creating Super-Linter helper script..."
cat > run-super-linter.sh << 'EOF'
#!/bin/bash

# Helper script to run Super-Linter locally
# Usage: ./run-super-linter.sh [--all]

VALIDATE_ALL_CODEBASE=${1:-false}

if [ "$1" = "--all" ]; then
    VALIDATE_ALL_CODEBASE=true
    echo "Running Super-Linter on all files..."
else
    VALIDATE_ALL_CODEBASE=false
    echo "Running Super-Linter on changed files only..."
fi

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
    -e YAML_CONFIG_FILE=Script/.yamllint.yml \
    -e MARKDOWN_CONFIG_FILE=Script/.markdownlint.yml \
    -e LOG_LEVEL=INFO \
    -e SUPPRESS_POSSUM=true \
    -v "$PWD":/tmp/lint \
    ghcr.io/super-linter/super-linter:v5.7.2
EOF

chmod +x run-super-linter.sh

print_success "Setup completed successfully!"
echo
echo "📋 What's been set up:"
echo "   ✅ Pre-commit hooks installed"
echo "   ✅ Super-Linter configuration ready"
echo "   ✅ Custom linting configurations applied"
echo "   ✅ Helper script created: run-super-linter.sh"
echo
echo "🎯 Usage:"
echo "   • Pre-commit hooks will run automatically on each commit"
echo "   • Run './run-super-linter.sh' to manually check changed files"
echo "   • Run './run-super-linter.sh --all' to check all files"
echo "   • Run 'pre-commit run --all-files' to run all hooks manually"
echo
echo "🔧 Common commands:"
echo "   • pre-commit run --hook-id=<hook-name>  # Run specific hook"
echo "   • pre-commit run --all-files            # Run all hooks on all files"
echo "   • pre-commit autoupdate                 # Update hook versions"
echo "   • pre-commit uninstall                  # Remove hooks (if needed)"
echo
print_success "Happy coding with automated quality checks! 🚀"
