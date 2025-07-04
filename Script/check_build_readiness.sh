#!/bin/bash

# GitHub Actions Build Readiness Checker
# Verifies all components needed for CI/CD to pass

set -euo pipefail

echo "🔍 GitHub Actions Build Readiness Check"
echo "======================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

success_count=0
error_count=0

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
}

echo ""
echo "1. Core Documentation Files"
echo "---------------------------"

required_files=(
    "README.md"
    "CONTRIBUTING.md"
    "LICENSE"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        log_success "$file exists"
    else
        log_error "$file missing"
    fi
done

echo ""
echo "2. YAML Syntax Validation"
echo "-------------------------"

# Check critical YAML files
yaml_files=(
    "Ansible/main.yml"
    "Ansible/inventory"
    "Ansible/vars/global.yml"
    "Ansible/ansible.cfg"
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
echo "3. Helm Charts Validation"
echo "-------------------------"

for chart_dir in Helm/*/; do
    chart_name=$(basename "$chart_dir")
    if [ -f "$chart_dir/Chart.yaml" ]; then
        if python3 -c "import yaml; yaml.safe_load(open('$chart_dir/Chart.yaml'))" 2>/dev/null; then
            log_success "Helm chart $chart_name has valid Chart.yaml"
        else
            log_error "Helm chart $chart_name has invalid Chart.yaml"
        fi
    else
        log_error "Helm chart $chart_name missing Chart.yaml"
    fi
done

echo ""
echo "4. Scripts and Executables"
echo "--------------------------"

critical_scripts=(
    "Script/validate_project.sh"
    "Script/validate_charts.sh"
    "Script/fix_yaml.py"
    "Script/manage_helm_dependencies.sh"
    "Test/helm_chart_tests.sh"
    "Test/run_all_tests.sh"
)

for script in "${critical_scripts[@]}"; do
    if [ -f "$script" ]; then
        if [ -x "$script" ]; then
            log_success "$script exists and is executable"
        else
            log_warning "$script exists but not executable"
            chmod +x "$script"
            log_success "Made $script executable"
        fi
    else
        log_error "$script missing"
    fi
done

echo ""
echo "5. Documentation Structure"
echo "--------------------------"

docs_files=(
    "docs/USER_GUIDE.md"
    "docs/charts/index.md"
    "docs/ansible/index.md"
    "docs/scripts/index.md"
)

for file in "${docs_files[@]}"; do
    if [ -f "$file" ]; then
        log_success "$file exists"
    else
        log_error "$file missing - will cause mkdocs build to fail"
    fi
done

echo ""
echo "6. Ansible Configuration"
echo "------------------------"

cd Ansible

# Test Ansible configuration
if ansible-config dump --only-changed >/dev/null 2>&1; then
    log_success "Ansible configuration is valid"
else
    log_error "Ansible configuration has errors"
fi

# Test inventory parsing
if ansible-inventory --list >/dev/null 2>&1; then
    log_success "Ansible inventory parses correctly"
else
    log_error "Ansible inventory has parsing errors"
fi

# Test playbook syntax
if ansible-playbook --syntax-check main.yml -i inventory >/dev/null 2>&1; then
    log_success "Ansible playbook syntax is valid"
else
    log_error "Ansible playbook has syntax errors"
fi

cd ..

echo ""
echo "7. GitHub Workflows"
echo "------------------"

workflows=(
    ".github/workflows/ci.yml"
    ".github/workflows/docs.yml"
)

for workflow in "${workflows[@]}"; do
    if [ -f "$workflow" ]; then
        if python3 -c "import yaml; yaml.safe_load(open('$workflow'))" 2>/dev/null; then
            log_success "GitHub workflow $workflow is valid"
        else
            log_error "GitHub workflow $workflow has YAML errors"
        fi
    else
        log_error "GitHub workflow $workflow missing"
    fi
done

echo ""
echo "8. Dependencies and Chart Structure"
echo "----------------------------------"

# Check GitLab chart specifically (most complex)
if [ -f "Helm/gitlab/Chart.yaml" ]; then
    if [ -d "Helm/gitlab/charts" ]; then
        log_success "GitLab chart has dependencies directory"
    else
        log_warning "GitLab chart missing dependencies directory"
    fi
    
    if [ -f "Helm/gitlab/Chart.lock" ]; then
        log_success "GitLab chart has Chart.lock file"
    else
        log_warning "GitLab chart missing Chart.lock (dependencies may need updating)"
    fi
fi

echo ""
echo "📊 Build Readiness Summary"
echo "=========================="
echo -e "✅ Checks passed: ${GREEN}$success_count${NC}"
echo -e "❌ Checks failed: ${RED}$error_count${NC}"

if [ $error_count -eq 0 ]; then
    echo -e "\n🎉 ${GREEN}Ready for GitHub Actions build!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Commit and push your changes"
    echo "2. GitHub Actions should pass all checks"
    echo "3. Documentation will be built and deployed"
    exit 0
else
    echo -e "\n💥 ${RED}Build readiness check failed${NC}"
    echo ""
    echo "Fix the errors above before pushing to GitHub"
    exit 1
fi
