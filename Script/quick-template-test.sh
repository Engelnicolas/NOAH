#!/bin/bash

# =============================================================================
# Quick Template Validation Script
# =============================================================================
# A simplified script to quickly validate all Helm chart templates
# This script focuses on basic template rendering validation

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
TOTAL_CHARTS=0
PASSED_CHARTS=0
FAILED_CHARTS=0

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HELM_DIR="$REPO_ROOT/Helm"

echo -e "${BLUE}🚀 Quick Template Validation${NC}"
echo -e "${BLUE}============================${NC}"
echo

# Setup Helm repositories
echo -e "${BLUE}Setting up Helm repositories...${NC}"
helm repo add bitnami https://charts.bitnami.com/bitnami >/dev/null 2>&1 || true
helm repo add elastic https://helm.elastic.co >/dev/null 2>&1 || true
helm repo update >/dev/null 2>&1
echo -e "${GREEN}✅ Repositories updated${NC}"
echo

# Find all charts
charts=()
for dir in "$HELM_DIR"/*; do
    if [[ -d "$dir" && -f "$dir/Chart.yaml" ]]; then
        charts+=("$dir")
    fi
done
TOTAL_CHARTS=${#charts[@]}

echo -e "${BLUE}Found $TOTAL_CHARTS charts to validate${NC}"
echo

# Validate each chart
for chart_dir in "${charts[@]}"; do
    chart_name=$(basename "$chart_dir")
    
    echo -n "Testing $chart_name... "
    
    # Check if it's a library chart (not installable)
    if grep -q "type: library" "$chart_dir/Chart.yaml" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Skipped (library chart)${NC}"
        continue
    fi
    
    # Build dependencies if needed
    if grep -q "dependencies:" "$chart_dir/Chart.yaml" 2>/dev/null; then
        helm dependency build "$chart_dir" >/dev/null 2>&1 || {
            echo -e "${RED}❌ (dependency build failed)${NC}"
            FAILED_CHARTS=$((FAILED_CHARTS + 1))
            continue
        }
    fi
    
    # Test template rendering
    if helm template test-release "$chart_dir" --dry-run >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Passed${NC}"
        PASSED_CHARTS=$((PASSED_CHARTS + 1))
    else
        echo -e "${RED}❌ Failed${NC}"
        FAILED_CHARTS=$((FAILED_CHARTS + 1))
        
        # Show error details
        echo -e "${YELLOW}Error details:${NC}"
        helm template test-release "$chart_dir" --dry-run 2>&1 | head -3 | sed 's/^/  /'
        echo
    fi
done

echo
echo -e "${BLUE}📊 Summary:${NC}"
echo -e "${GREEN}  ✅ Passed: $PASSED_CHARTS${NC}"
echo -e "${RED}  ❌ Failed: $FAILED_CHARTS${NC}"
echo -e "${BLUE}  📊 Total:  $TOTAL_CHARTS${NC}"

# Calculate success rate
if [[ $TOTAL_CHARTS -gt 0 ]]; then
    success_rate=$((PASSED_CHARTS * 100 / TOTAL_CHARTS))
    echo -e "${BLUE}  📈 Success Rate: $success_rate%${NC}"
fi

echo

# Exit with appropriate code
if [[ $FAILED_CHARTS -eq 0 ]]; then
    echo -e "${GREEN}🎉 All templates validated successfully!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some templates failed validation${NC}"
    exit 1
fi
