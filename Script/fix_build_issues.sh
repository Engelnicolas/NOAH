#!/bin/bash
# =============================================================================
# NOAH - Complete YAML and Build Fix Script
# =============================================================================
# This script fixes all common issues that can cause GitHub Actions to fail

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

fix_yaml_trailing_spaces() {
    log_info "Fixing trailing spaces in YAML files..."
    
    # Find and fix trailing spaces
    find "$PROJECT_ROOT" -name "*.yml" -o -name "*.yaml" | while read -r file; do
        if [[ -f "$file" ]]; then
            # Remove trailing spaces
            sed -i 's/[[:space:]]*$//' "$file"
        fi
    done
    
    log_success "Fixed trailing spaces in YAML files"
}

fix_yaml_newlines() {
    log_info "Ensuring all files end with newline..."
    
    find "$PROJECT_ROOT" -name "*.yml" -o -name "*.yaml" -o -name "*.md" -o -name "*.sh" | while read -r file; do
        if [[ -f "$file" && -s "$file" ]]; then
            # Check if file ends with newline
            if [[ $(tail -c1 "$file" | wc -l) -eq 0 ]]; then
                echo "" >> "$file"
            fi
        fi
    done
    
    log_success "Ensured all files end with newline"
}

fix_script_permissions() {
    log_info "Fixing script permissions..."
    
    # Make all shell scripts executable
    find "$PROJECT_ROOT/Script" -name "*.sh" -exec chmod +x {} \;
    find "$PROJECT_ROOT/Test" -name "*.sh" -exec chmod +x {} \;
    
    log_success "Fixed script permissions"
}

validate_critical_files() {
    log_info "Validating critical files exist..."
    
    local missing_files=()
    
    # Check critical files
    local critical_files=(
        "mkdocs.yml"
        "LICENSE"
        "CONTRIBUTING.md"
        "README.md"
        "docs/index.md"
        "docs/LICENSE.md"
        "docs/USER_GUIDE.md"
        "docs/charts/index.md"
        "docs/ansible/index.md"
        "docs/scripts/index.md"
        ".github/workflows/ci.yml"
        ".github/workflows/docs.yml"
        ".github/workflows/release.yml"
        ".github/workflows/dependencies.yml"
        "Ansible/main.yml"
        "Ansible/inventory"
        "Ansible/ansible.cfg"
        "Ansible/requirements.yml"
        "Ansible/vars/global.yml"
    )
    
    for file in "${critical_files[@]}"; do
        if [[ ! -f "$PROJECT_ROOT/$file" ]]; then
            missing_files+=("$file")
        fi
    done
    
    if [[ ${#missing_files[@]} -eq 0 ]]; then
        log_success "All critical files exist"
        return 0
    else
        log_error "Missing critical files:"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        return 1
    fi
}

create_missing_chart_files() {
    log_info "Checking Helm chart structure..."
    
    # Check if all Helm charts have required files
    for chart_dir in "$PROJECT_ROOT/Helm"/*; do
        if [[ -d "$chart_dir" ]]; then
            chart_name=$(basename "$chart_dir")
            
            # Check Chart.yaml
            if [[ ! -f "$chart_dir/Chart.yaml" ]]; then
                log_warning "Creating missing Chart.yaml for $chart_name"
                cat > "$chart_dir/Chart.yaml" << EOF
apiVersion: v2
name: $chart_name
description: A Helm chart for $chart_name
type: application
version: 1.0.0
appVersion: "1.0.0"
EOF
            fi
            
            # Check values.yaml
            if [[ ! -f "$chart_dir/values.yaml" ]]; then
                log_warning "Creating missing values.yaml for $chart_name"
                cat > "$chart_dir/values.yaml" << EOF
# Default values for $chart_name
replicaCount: 1

image:
  repository: $chart_name
  pullPolicy: IfNotPresent
  tag: ""

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: false

resources: {}
nodeSelector: {}
tolerations: []
affinity: {}
EOF
            fi
            
            # Check templates directory
            if [[ ! -d "$chart_dir/templates" ]]; then
                log_warning "Creating missing templates directory for $chart_name"
                mkdir -p "$chart_dir/templates"
                
                # Create basic service template
                cat > "$chart_dir/templates/service.yaml" << EOF
apiVersion: v1
kind: Service
metadata:
  name: {{ include "$chart_name.fullname" . }}
  labels:
    {{- include "$chart_name.labels" . | nindent 4 }}
spec:
  type: {{ .Values.service.type }}
  ports:
    - port: {{ .Values.service.port }}
      targetPort: http
      protocol: TCP
      name: http
  selector:
    {{- include "$chart_name.selectorLabels" . | nindent 4 }}
EOF
            fi
        fi
    done
    
    log_success "Helm chart structure validated"
}

update_github_actions() {
    log_info "Validating GitHub Actions workflows..."
    
    # Check if workflows use current action versions
    local workflows_dir="$PROJECT_ROOT/.github/workflows"
    
    for workflow in "$workflows_dir"/*.yml; do
        if [[ -f "$workflow" ]]; then
            # Check for deprecated actions
            if grep -q "actions/checkout@v3" "$workflow"; then
                log_warning "Updating checkout action to v4 in $(basename "$workflow")"
                sed -i 's/actions\/checkout@v3/actions\/checkout@v4/g' "$workflow"
            fi
            
            if grep -q "actions/setup-python@v4" "$workflow"; then
                log_warning "Updating setup-python action to v5 in $(basename "$workflow")"
                sed -i 's/actions\/setup-python@v4/actions\/setup-python@v5/g' "$workflow"
            fi
            
            if grep -q "actions/upload-artifact@v3" "$workflow"; then
                log_warning "Updating upload-artifact action to v4 in $(basename "$workflow")"
                sed -i 's/actions\/upload-artifact@v3/actions\/upload-artifact@v4/g' "$workflow"
            fi
        fi
    done
    
    log_success "GitHub Actions workflows validated"
}

main() {
    log_info "Starting NOAH Build Fix Process..."
    echo ""
    
    cd "$PROJECT_ROOT"
    
    # Step 1: Fix YAML formatting issues
    fix_yaml_trailing_spaces
    fix_yaml_newlines
    
    # Step 2: Fix script permissions
    fix_script_permissions
    
    # Step 3: Validate critical files
    if ! validate_critical_files; then
        log_error "Some critical files are missing. Please create them manually."
    fi
    
    # Step 4: Create missing Helm chart files
    create_missing_chart_files
    
    # Step 5: Update GitHub Actions
    update_github_actions
    
    echo ""
    log_success "🎉 Build fix process completed!"
    echo ""
    log_info "Next steps:"
    echo "  1. Run: ./Script/validate_yaml.py"
    echo "  2. Test Ansible syntax: ansible-playbook --syntax-check Ansible/main.yml -i Ansible/inventory"
    echo "  3. Test Helm charts: helm lint Helm/*/"
    echo "  4. Build docs: mkdocs build"
    echo ""
    log_info "If all tests pass, your repository is ready for GitHub Actions!"
}

# Run main function
main "$@"
