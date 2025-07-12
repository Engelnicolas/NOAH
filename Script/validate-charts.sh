#!/bin/bash
set -e

# NOAH Helm Charts Validation Script
# ===================================
# This script validates all Helm charts in the repository
# Usage: ./validate-charts.sh [--fix] [--verbose]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HELM_DIR="$REPO_ROOT/Helm"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Flags
FIX_MODE=false
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            FIX_MODE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--fix] [--verbose]"
            echo "  --fix     Automatically fix common issues"
            echo "  --verbose Show detailed output"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    if ! command -v helm &> /dev/null; then
        error "Helm is not installed. Please install Helm 3.x"
        exit 1
    fi
    
    if ! command -v yamllint &> /dev/null; then
        error "yamllint is not installed. Run: pip install yamllint"
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Add Helm repositories
setup_helm_repos() {
    log "Setting up Helm repositories..."
    
    helm repo add bitnami https://charts.bitnami.com/bitnami >/dev/null 2>&1 || true
    helm repo add elastic https://helm.elastic.co >/dev/null 2>&1 || true
    helm repo update >/dev/null 2>&1
    
    success "Helm repositories updated"
}

# Build dependencies
build_dependencies() {
    log "Building Helm chart dependencies..."
    
    local failed_charts=()
    
    for chart_dir in "$HELM_DIR"/*; do
        if [[ -d "$chart_dir" && -f "$chart_dir/Chart.yaml" ]]; then
            chart_name=$(basename "$chart_dir")
            
            if grep -q "dependencies:" "$chart_dir/Chart.yaml" 2>/dev/null; then
                if [[ "$VERBOSE" == "true" ]]; then
                    log "Building dependencies for $chart_name..."
                fi
                
                if helm dependency build "$chart_dir" >/dev/null 2>&1; then
                    success "Dependencies built for $chart_name"
                else
                    error "Failed to build dependencies for $chart_name"
                    failed_charts+=("$chart_name")
                fi
            else
                if [[ "$VERBOSE" == "true" ]]; then
                    log "No dependencies for $chart_name"
                fi
            fi
        fi
    done
    
    if [[ ${#failed_charts[@]} -gt 0 ]]; then
        error "Failed to build dependencies for: ${failed_charts[*]}"
        return 1
    fi
}

# Validate YAML syntax
validate_yaml() {
    log "Validating YAML syntax..."
    
    if yamllint --config-file="$REPO_ROOT/Script/.yamllint.yml" "$HELM_DIR"/*/values.yaml "$HELM_DIR"/*/Chart.yaml; then
        success "YAML syntax validation passed"
    else
        error "YAML syntax validation failed"
        if [[ "$FIX_MODE" == "true" ]]; then
            warning "Attempting to fix trailing spaces..."
            find "$HELM_DIR" -name "*.yaml" -exec sed -i 's/[[:space:]]*$//' {} \;
            warning "Fixed trailing spaces. Please review changes."
        fi
        return 1
    fi
}

# Lint Helm charts
lint_charts() {
    log "Linting Helm charts..."
    
    local failed_charts=()
    local total_charts=0
    
    for chart_dir in "$HELM_DIR"/*; do
        if [[ -d "$chart_dir" && -f "$chart_dir/Chart.yaml" ]]; then
            chart_name=$(basename "$chart_dir")
            total_charts=$((total_charts + 1))
            
            if [[ "$VERBOSE" == "true" ]]; then
                log "Linting $chart_name..."
            fi
            
            if helm lint "$chart_dir" >/dev/null 2>&1; then
                if [[ "$VERBOSE" == "true" ]]; then
                    success "$chart_name linting passed"
                fi
            else
                error "$chart_name linting failed"
                failed_charts+=("$chart_name")
                
                if [[ "$VERBOSE" == "true" ]]; then
                    helm lint "$chart_dir"
                fi
            fi
        fi
    done
    
    if [[ ${#failed_charts[@]} -gt 0 ]]; then
        error "Chart linting failed for: ${failed_charts[*]}"
        return 1
    else
        success "All $total_charts charts passed linting"
    fi
}

# Test template rendering
test_templates() {
    log "Testing template rendering..."
    
    local failed_charts=()
    local total_charts=0
    
    for chart_dir in "$HELM_DIR"/*; do
        if [[ -d "$chart_dir" && -f "$chart_dir/Chart.yaml" ]]; then
            chart_name=$(basename "$chart_dir")
            total_charts=$((total_charts + 1))
            
            if [[ "$VERBOSE" == "true" ]]; then
                log "Testing template rendering for $chart_name..."
            fi
            
            if helm template "test-$chart_name" "$chart_dir" --debug --dry-run >/dev/null 2>&1; then
                if [[ "$VERBOSE" == "true" ]]; then
                    success "$chart_name template rendering passed"
                fi
            else
                error "$chart_name template rendering failed"
                failed_charts+=("$chart_name")
                
                if [[ "$VERBOSE" == "true" ]]; then
                    helm template "test-$chart_name" "$chart_dir" --debug --dry-run
                fi
            fi
        fi
    done
    
    if [[ ${#failed_charts[@]} -gt 0 ]]; then
        error "Template rendering failed for: ${failed_charts[*]}"
        return 1
    else
        success "All $total_charts charts rendered successfully"
    fi
}

# Generate summary report
generate_report() {
    log "Generating validation summary..."
    
    local total_charts=0
    echo ""
    echo "📊 NOAH Helm Charts Summary"
    echo "=========================="
    
    for chart_dir in "$HELM_DIR"/*; do
        if [[ -d "$chart_dir" && -f "$chart_dir/Chart.yaml" ]]; then
            chart_name=$(basename "$chart_dir")
            chart_version=$(grep "^version:" "$chart_dir/Chart.yaml" | awk '{print $2}')
            app_version=$(grep "^appVersion:" "$chart_dir/Chart.yaml" | awk '{print $2}' | tr -d '"')
            
            echo "  📦 $chart_name (v$chart_version) - App: $app_version"
            total_charts=$((total_charts + 1))
        fi
    done
    
    echo ""
    echo "Total Charts: $total_charts"
    echo ""
}

# Main execution
main() {
    echo "🚀 NOAH Helm Charts Validation"
    echo "==============================="
    echo ""
    
    check_prerequisites
    setup_helm_repos
    
    local exit_code=0
    
    # Run all validation steps
    build_dependencies || exit_code=1
    validate_yaml || exit_code=1
    lint_charts || exit_code=1
    test_templates || exit_code=1
    
    generate_report
    
    if [[ $exit_code -eq 0 ]]; then
        success "All validations passed! 🎉"
    else
        error "Some validations failed. Please review the errors above."
    fi
    
    exit $exit_code
}

# Run main function
main "$@"
