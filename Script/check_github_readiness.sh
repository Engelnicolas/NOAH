#!/bin/bash
# =============================================================================
# NOAH - Build Readiness Validation Script
# =============================================================================
# This script validates that all components are ready for GitHub Actions CI/CD
# It checks YAML syntax, Ansible playbooks, Helm charts, and documentation.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# Log functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED_CHECKS++))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED_CHECKS++))
}

check_command() {
    ((TOTAL_CHECKS++))
    if command -v "$1" &> /dev/null; then
        log_success "Command '$1' is available"
        return 0
    else
        log_error "Command '$1' is not available"
        return 1
    fi
}

check_file_exists() {
    ((TOTAL_CHECKS++))
    if [[ -f "$1" ]]; then
        log_success "File exists: $1"
        return 0
    else
        log_error "File missing: $1"
        return 1
    fi
}

check_dir_exists() {
    ((TOTAL_CHECKS++))
    if [[ -d "$1" ]]; then
        log_success "Directory exists: $1"
        return 0
    else
        log_error "Directory missing: $1"
        return 1
    fi
}

validate_yaml() {
    local file="$1"
    ((TOTAL_CHECKS++))
    
    if python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
        log_success "YAML valid: $(basename "$file")"
        return 0
    else
        log_error "YAML invalid: $(basename "$file")"
        return 1
    fi
}

validate_ansible_syntax() {
    ((TOTAL_CHECKS++))
    
    cd "$PROJECT_ROOT/Ansible"
    
    if ansible-playbook --syntax-check main.yml -i inventory &>/dev/null; then
        log_success "Ansible syntax check passed"
        return 0
    else
        log_error "Ansible syntax check failed"
        return 1
    fi
}

validate_helm_chart() {
    local chart_dir="$1"
    local chart_name=$(basename "$chart_dir")
    ((TOTAL_CHECKS++))
    
    if [[ -f "$chart_dir/Chart.yaml" ]]; then
        if helm lint "$chart_dir" &>/dev/null; then
            log_success "Helm chart valid: $chart_name"
            return 0
        else
            log_error "Helm chart invalid: $chart_name"
            return 1
        fi
    else
        log_error "Chart.yaml missing in: $chart_name"
        return 1
    fi
}

main() {
    log_info "Starting NOAH Build Readiness Check..."
    echo ""
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # 1. Check required commands
    log_info "=== Checking Required Commands ==="
    check_command "python3"
    check_command "ansible-playbook"
    check_command "helm"
    check_command "git"
    echo ""
    
    # 2. Check critical files
    log_info "=== Checking Critical Files ==="
    check_file_exists "mkdocs.yml"
    check_file_exists "LICENSE"
    check_file_exists "CONTRIBUTING.md"
    check_file_exists "README.md"
    check_file_exists "docs/index.md"
    check_file_exists "docs/LICENSE.md"
    check_file_exists "docs/USER_GUIDE.md"
    echo ""
    
    # 3. Check GitHub Actions workflows
    log_info "=== Checking GitHub Actions Workflows ==="
    check_file_exists ".github/workflows/ci.yml"
    check_file_exists ".github/workflows/docs.yml"
    check_file_exists ".github/workflows/release.yml"
    check_file_exists ".github/workflows/dependencies.yml"
    echo ""
    
    # 4. Validate GitHub Actions YAML
    log_info "=== Validating GitHub Actions YAML ==="
    for workflow in .github/workflows/*.yml; do
        if [[ -f "$workflow" ]]; then
            validate_yaml "$workflow"
        fi
    done
    echo ""
    
    # 5. Check Ansible structure
    log_info "=== Checking Ansible Structure ==="
    check_dir_exists "Ansible"
    check_file_exists "Ansible/main.yml"
    check_file_exists "Ansible/inventory"
    check_file_exists "Ansible/ansible.cfg"
    check_file_exists "Ansible/requirements.yml"
    check_dir_exists "Ansible/roles"
    echo ""
    
    # 6. Validate Ansible YAML files
    log_info "=== Validating Ansible YAML ==="
    validate_yaml "Ansible/main.yml"
    validate_yaml "Ansible/inventory"
    validate_yaml "Ansible/requirements.yml"
    validate_yaml "Ansible/vars/global.yml"
    echo ""
    
    # 7. Validate Ansible syntax
    log_info "=== Validating Ansible Syntax ==="
    if command -v ansible-playbook &> /dev/null; then
        validate_ansible_syntax
    else
        log_warning "Skipping Ansible syntax check (ansible-playbook not available)"
    fi
    echo ""
    
    # 8. Check Helm structure
    log_info "=== Checking Helm Structure ==="
    check_dir_exists "Helm"
    
    # Check each Helm chart
    for chart_dir in Helm/*/; do
        if [[ -d "$chart_dir" ]]; then
            chart_name=$(basename "$chart_dir")
            check_file_exists "$chart_dir/Chart.yaml"
            check_file_exists "$chart_dir/values.yaml"
            check_dir_exists "$chart_dir/templates"
        fi
    done
    echo ""
    
    # 9. Validate Helm charts
    log_info "=== Validating Helm Charts ==="
    if command -v helm &> /dev/null; then
        for chart_dir in Helm/*/; do
            if [[ -d "$chart_dir" ]]; then
                validate_helm_chart "$chart_dir"
            fi
        done
    else
        log_warning "Skipping Helm validation (helm not available)"
    fi
    echo ""
    
    # 10. Check Scripts structure
    log_info "=== Checking Scripts Structure ==="
    check_dir_exists "Script"
    check_file_exists "Script/setup_infra.sh"
    check_file_exists "Script/validate_project.sh"
    check_file_exists "Script/manage_helm_dependencies.sh"
    echo ""
    
    # 11. Check script permissions
    log_info "=== Checking Script Permissions ==="
    for script in Script/*.sh Test/*.sh; do
        if [[ -f "$script" ]]; then
            ((TOTAL_CHECKS++))
            if [[ -x "$script" ]]; then
                log_success "Script executable: $(basename "$script")"
            else
                log_error "Script not executable: $(basename "$script")"
                # Fix the permission
                chmod +x "$script"
                log_info "Fixed permissions for: $(basename "$script")"
            fi
        fi
    done
    echo ""
    
    # 12. Check Test structure
    log_info "=== Checking Test Structure ==="
    check_dir_exists "Test"
    check_file_exists "Test/run_all_tests.sh"
    echo ""
    
    # 13. Check documentation structure
    log_info "=== Checking Documentation Structure ==="
    check_dir_exists "docs"
    check_dir_exists "docs/charts"
    check_dir_exists "docs/ansible"
    check_dir_exists "docs/scripts"
    check_file_exists "docs/charts/index.md"
    check_file_exists "docs/ansible/index.md"
    check_file_exists "docs/scripts/index.md"
    echo ""
    
    # 14. Validate MkDocs configuration
    log_info "=== Validating MkDocs Configuration ==="
    validate_yaml "mkdocs.yml"
    
    # Check if all referenced files in nav exist
    if command -v python3 &> /dev/null; then
        ((TOTAL_CHECKS++))
        python3 -c "
import yaml
import os

with open('mkdocs.yml') as f:
    config = yaml.safe_load(f)

def check_nav_files(nav, path='docs/'):
    for item in nav:
        if isinstance(item, dict):
            for key, value in item.items():
                if isinstance(value, str):
                    file_path = os.path.join(path, value)
                    if not os.path.exists(file_path):
                        print(f'Missing nav file: {file_path}')
                        exit(1)
                elif isinstance(value, list):
                    check_nav_files(value, path)

if 'nav' in config:
    check_nav_files(config['nav'])
print('All navigation files exist')
" 2>/dev/null && log_success "All MkDocs navigation files exist" || log_error "Some MkDocs navigation files are missing"
    else
        log_warning "Skipping MkDocs file check (python3 not available)"
    fi
    echo ""
    
    # 15. Check for common CI/CD issues
    log_info "=== Checking for Common CI/CD Issues ==="
    
    # Check for trailing spaces in YAML files
    ((TOTAL_CHECKS++))
    if find . -name "*.yml" -o -name "*.yaml" | xargs grep -l '[[:space:]]$' 2>/dev/null | head -1 &>/dev/null; then
        log_error "Found trailing spaces in YAML files"
        echo "  Run: ./Script/fix_yaml_linting.sh to fix"
    else
        log_success "No trailing spaces in YAML files"
    fi
    
    # Check for files without newline at EOF
    ((TOTAL_CHECKS++))
    files_without_newline=0
    for file in $(find . -name "*.yml" -o -name "*.yaml" -o -name "*.md" | head -20); do
        if [[ -f "$file" && -s "$file" ]]; then
            if [[ $(tail -c1 "$file" | wc -l) -eq 0 ]]; then
                ((files_without_newline++))
            fi
        fi
    done
    
    if [[ $files_without_newline -eq 0 ]]; then
        log_success "All checked files end with newline"
    else
        log_error "$files_without_newline files don't end with newline"
        echo "  Run: ./Script/fix_yaml_linting.sh to fix"
    fi
    echo ""
    
    # Summary
    log_info "=== Build Readiness Summary ==="
    echo "Total checks: $TOTAL_CHECKS"
    echo -e "Passed: ${GREEN}$PASSED_CHECKS${NC}"
    echo -e "Failed: ${RED}$FAILED_CHECKS${NC}"
    echo ""
    
    if [[ $FAILED_CHECKS -eq 0 ]]; then
        log_success "🎉 All checks passed! Repository is ready for GitHub Actions build."
        exit 0
    else
        log_error "❌ $FAILED_CHECKS checks failed. Please fix the issues before pushing."
        echo ""
        log_info "Quick fixes:"
        echo "  • Run: ./Script/fix_yaml_linting.sh"
        echo "  • Run: ./Script/validate_project.sh"
        echo "  • Run: ./Script/manage_helm_dependencies.sh"
        echo "  • Ensure all required files exist"
        exit 1
    fi
}

# Run main function
main "$@"
