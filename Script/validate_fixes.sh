#!/bin/bash

# Validation script to verify all linting fixes
set -euo pipefail

echo "🔍 Validating NOAH Project Fixes"
echo "================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

success=0
errors=0

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((success++))
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
    ((errors++))
}

log_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

echo ""
echo "1. YAML Syntax Validation"
echo "-------------------------"

# Check key YAML files
yaml_files=(
    "Ansible/main.yml"
    "Ansible/inventory"
    "Ansible/vars/global.yml"
    "Helm/gitlab/Chart.yaml"
    "Helm/gitlab/values.yaml"
)

for file in "${yaml_files[@]}"; do
    if [ -f "$file" ]; then
        if python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
            log_success "YAML syntax valid: $file"
        else
            log_error "YAML syntax error: $file"
        fi
    else
        log_error "Missing file: $file"
    fi
done

echo ""
echo "2. Ansible Configuration Validation"
echo "-----------------------------------"

cd Ansible

# Test inventory parsing
if ansible-inventory --list >/dev/null 2>&1; then
    log_success "Ansible inventory parses correctly"
else
    log_error "Ansible inventory has errors"
fi

# Test playbook syntax
if ansible-playbook --syntax-check main.yml -i inventory >/dev/null 2>&1; then
    log_success "Ansible playbook syntax is valid"
else
    log_error "Ansible playbook has syntax errors"
fi

cd ..

echo ""
echo "3. Helm Chart Validation"
echo "------------------------"

# Check gitlab chart structure
if [ -f "Helm/gitlab/Chart.yaml" ]; then
    log_success "GitLab Chart.yaml exists"
else
    log_error "GitLab Chart.yaml missing"
fi

if [ -f "Helm/gitlab/templates/gitlab-secret.yaml" ]; then
    log_success "gitlab-secret.yaml template exists"
else
    log_error "gitlab-secret.yaml template missing"
fi

if [ -d "Helm/gitlab/charts" ]; then
    log_success "Charts directory exists"
    
    if [ -d "Helm/gitlab/charts/postgresql" ] && [ -d "Helm/gitlab/charts/redis" ]; then
        log_success "Required dependencies (postgresql, redis) are present"
    else
        log_error "Missing dependency charts"
    fi
else
    log_error "Charts directory missing"
fi

echo ""
echo "4. File Structure Validation"
echo "----------------------------"

required_files=(
    "CONTRIBUTING.md"
    "LICENSE"
    "README.md"
    "docs/index.md"
    "docs/USER_GUIDE.md"
    "docs/ENHANCEMENT_STATUS.md"
    "docs/charts/index.md"
    "docs/ansible/index.md"
    "docs/scripts/index.md"
    "mkdocs.yml"
    "Script/fix_yaml.py"
    "Script/fix_yaml_linting.sh"
    "Script/validate_project.sh"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        log_success "Required file exists: $file"
    else
        log_error "Missing required file: $file"
    fi
done

echo ""
echo "5. Trailing Spaces Check"
echo "------------------------"

trailing_spaces=$(find . -name "*.yml" -o -name "*.yaml" | grep -v ".git" | grep -v "charts/" | xargs grep -l '[[:space:]]$' 2>/dev/null || true)

if [ -z "$trailing_spaces" ]; then
    log_success "No trailing spaces found in YAML files"
else
    log_error "Files with trailing spaces found: $trailing_spaces"
fi

echo ""
echo "6. Documentation Merge Validation"
echo "---------------------------------"

# Check that old Docs/ directory has been removed
if [ -d "Docs" ]; then
    log_error "Old Docs/ directory still exists - should be removed after merge"
else
    log_success "Old Docs/ directory successfully removed"
fi

# Check that required files exist in docs/
required_docs=(
    "docs/index.md"
    "docs/USER_GUIDE.md"
    "docs/ENHANCEMENT_STATUS.md"
    "docs/CONTRIBUTING.md"
    "docs/LICENSE.md"
    "docs/charts/index.md"
    "docs/ansible/index.md"
    "docs/scripts/index.md"
    "docs/DIRECTORY_MERGE_SUMMARY.md"
)

for file in "${required_docs[@]}"; do
    if [ -f "$file" ]; then
        log_success "Documentation file exists: $file"
    else
        log_error "Missing documentation file: $file"
    fi
done

# Check for any remaining references to old Docs/ directory
docs_refs=$(grep -r "Docs/" . --exclude-dir=.git --exclude-dir=.venv --exclude="*.log" 2>/dev/null | grep -v "docs/" | grep -v "mkdocs" | grep -v "Documentation:" | head -5 || true)

if [ -z "$docs_refs" ]; then
    log_success "No remaining references to old Docs/ directory found"
else
    log_error "Found references to old Docs/ directory: $docs_refs"
fi

echo ""
echo "📊 Validation Summary"
echo "===================="
echo -e "✅ Successes: ${GREEN}$success${NC}"
echo -e "❌ Errors:    ${RED}$errors${NC}"

if [ $errors -eq 0 ]; then
    echo -e "\n🎉 ${GREEN}All validations passed!${NC}"
    exit 0
else
    echo -e "\n💥 ${RED}Validation failed with $errors errors${NC}"
    exit 1
fi
