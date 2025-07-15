#!/bin/bash
# NOAH - Post-deployment validation
# This script runs the unified test suite after a deployment.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Execute the unified test suite with any passed arguments
./unified_tests.sh "$@"
