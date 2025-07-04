#!/bin/bash

# Comprehensive validation script for NOAH project
# Tests YAML syntax, Ansible inventory, and Helm charts

set -euo pipefail

echo "🔍 NOAH Project Validation Suite"
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

success_count=0
error_count=0
warning_count=0

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((success_count++))
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
    ((error_count++))
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    ((warning_count++))
}

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# 1. YAML Syntax Validation
echo ""
echo "🔧 1. YAML Syntax Validation"
echo "----------------------------"

yaml_files=$(find . -name "*.yml" -o -name "*.yaml" | grep -v node_modules | grep -v .git | grep -v charts/)

for file in $yaml_files; do
    if python3 -c "
import yaml
import sys
try:
    with open('$file', 'r') as f:
        yaml.safe_load(f)
    print('✓ $file')
except yaml.YAMLError as e:
    print('✗ $file: YAML Error -', str(e))
    sys.exit(1)
except Exception as e:
    print('✗ $file: Error -', str(e))
    sys.exit(1)
" 2>/dev/null; then
        continue
    else
        log_error "YAML syntax error in $file"
    fi
done

log_success "YAML syntax validation completed"

# 2. Ansible Inventory Validation
echo ""
echo "🎭 2. Ansible Inventory Validation"
echo "----------------------------------"

cd Ansible

if ansible-inventory --list > /dev/null 2>&1; then
    log_success "Ansible inventory is valid"
else
    log_error "Ansible inventory has errors"
fi

if ansible-playbook --syntax-check main.yml -i inventory > /dev/null 2>&1; then
    log_success "Ansible playbook syntax is valid"
else
    log_error "Ansible playbook syntax errors found"
fi

cd ..

# 3. Helm Chart Validation
echo ""
echo "⛵ 3. Helm Chart Validation"
echo "--------------------------"

if command -v helm >/dev/null 2>&1; then
    for chart_dir in Helm/*/; do
        chart_name=$(basename "$chart_dir")
        echo "Validating chart: $chart_name"
        
        if helm lint "$chart_dir" > /dev/null 2>&1; then
            log_success "Helm chart $chart_name passes lint"
        else
            log_error "Helm chart $chart_name has lint errors"
        fi
        
        if helm template test "$chart_dir" > /dev/null 2>&1; then
            log_success "Helm chart $chart_name templates render correctly"
        else
            log_warning "Helm chart $chart_name has template issues"
        fi
    done
else
    log_warning "Helm not installed - skipping Helm validation"
fi

# 4. Shell Script Validation
echo ""
echo "🐚 4. Shell Script Validation"
echo "-----------------------------"

for script in Script/*.sh; do
    if [ -f "$script" ]; then
        if bash -n "$script" 2>/dev/null; then
            log_success "Shell script $script syntax is valid"
        else
            log_error "Shell script $script has syntax errors"
        fi
    fi
done

# 5. File Structure Validation
echo ""
echo "📁 5. File Structure Validation"
echo "-------------------------------"

required_files=(
    "README.md"
    "CONTRIBUTING.md"
    "LICENSE"
    "Ansible/main.yml"
    "Ansible/inventory"
    "Ansible/ansible.cfg"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        log_success "Required file $file exists"
    else
        log_error "Required file $file is missing"
    fi
done

# Summary
echo ""
echo "📊 Validation Summary"
echo "===================="
echo -e "✅ Successes: ${GREEN}$success_count${NC}"
echo -e "⚠️  Warnings:  ${YELLOW}$warning_count${NC}"
echo -e "❌ Errors:    ${RED}$error_count${NC}"

if [ $error_count -eq 0 ]; then
    echo -e "\n🎉 ${GREEN}All critical validations passed!${NC}"
    exit 0
else
    echo -e "\n💥 ${RED}Validation failed with $error_count errors${NC}"
    exit 1
fi
