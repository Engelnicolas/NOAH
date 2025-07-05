#!/bin/bash

# N.O.A.H Unified Test Script
# ===========================
# Simplified test script that combines essential testing functionality

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="/tmp/noah_tests_$(date +%Y%m%d_%H%M%S).log"
TEST_NAMESPACE="noah-test"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$LOG_FILE"
}

info() {
    log "INFO" "${BLUE}$*${NC}"
}

success() {
    log "SUCCESS" "${GREEN}$*${NC}"
}

warn() {
    log "WARN" "${YELLOW}$*${NC}"
}

error() {
    log "ERROR" "${RED}$*${NC}"
}

# Helper functions
check_dependency() {
    if command -v "$1" >/dev/null 2>&1; then
        info "✅ $1 is available"
        return 0
    else
        warn "❌ $1 is not available"
        return 1
    fi
}

# Test functions
test_dependencies() {
    info "🔍 Checking dependencies..."
    
    local all_good=true
    
    # Required
    check_dependency "python3" || all_good=false
    
    # Optional but recommended
    check_dependency "helm" || warn "Helm not available - some tests will be skipped"
    check_dependency "kubectl" || warn "kubectl not available - K8s tests will be skipped"
    check_dependency "docker" || warn "Docker not available - container tests will be skipped"
    
    if [ "$all_good" = true ]; then
        success "All required dependencies are available"
        return 0
    else
        error "Some required dependencies are missing"
        return 1
    fi
}

test_python_suite() {
    info "🐍 Running Python test suite..."
    
    cd "$SCRIPT_DIR"
    
    if [ ! -f "noah_test.py" ]; then
        error "noah_test.py not found"
        return 1
    fi
    
    if python3 noah_test.py -v; then
        success "Python test suite passed"
        return 0
    else
        error "Python test suite failed"
        return 1
    fi
}

test_helm_charts_basic() {
    info "⛑️  Running basic Helm chart tests..."
    
    if ! check_dependency "helm"; then
        warn "Helm not available, skipping Helm tests"
        return 0
    fi
    
    local chart_dir="$PROJECT_ROOT/Helm"
    local failed_charts=()
    
    if [ ! -d "$chart_dir" ]; then
        error "Helm charts directory not found: $chart_dir"
        return 1
    fi
    
    for chart in "$chart_dir"/*; do
        if [ -d "$chart" ]; then
            local chart_name=$(basename "$chart")
            info "  Testing chart: $chart_name"
            
            if helm lint "$chart" >/dev/null 2>&1; then
                info "    ✅ $chart_name: Lint passed"
            else
                error "    ❌ $chart_name: Lint failed"
                failed_charts+=("$chart_name")
            fi
            
            if helm template test "$chart" >/dev/null 2>&1; then
                info "    ✅ $chart_name: Template rendering passed"
            else
                error "    ❌ $chart_name: Template rendering failed"
                failed_charts+=("$chart_name")
            fi
        fi
    done
    
    if [ ${#failed_charts[@]} -eq 0 ]; then
        success "All Helm charts passed basic tests"
        return 0
    else
        error "Failed charts: ${failed_charts[*]}"
        return 1
    fi
}

test_yaml_syntax() {
    info "📝 Testing YAML syntax..."
    
    local failed_files=()
    
    # Test key YAML files
    local yaml_files=(
        "$SCRIPT_DIR/test_config.yaml"
        "$PROJECT_ROOT/Ansible/vars/global.yml"
        "$PROJECT_ROOT/Script/.yamllint.yml"
    )
    
    for yaml_file in "${yaml_files[@]}"; do
        if [ -f "$yaml_file" ]; then
            if python3 -c "import yaml; yaml.safe_load(open('$yaml_file'))" >/dev/null 2>&1; then
                info "  ✅ $(basename "$yaml_file"): Valid YAML"
            else
                error "  ❌ $(basename "$yaml_file"): Invalid YAML"
                failed_files+=("$(basename "$yaml_file")")
            fi
        else
            warn "  ⚠️  $(basename "$yaml_file"): File not found"
        fi
    done
    
    if [ ${#failed_files[@]} -eq 0 ]; then
        success "All YAML files have valid syntax"
        return 0
    else
        error "Failed YAML files: ${failed_files[*]}"
        return 1
    fi
}

test_security_basic() {
    info "🔒 Running basic security tests..."
    
    local security_issues=()
    
    # Check for .gitignore
    if [ ! -f "$PROJECT_ROOT/.gitignore" ]; then
        security_issues+=("Missing .gitignore file")
    fi
    
    # Basic secret scanning (look for common patterns)
    if grep -r -i --exclude-dir=.git --exclude-dir=node_modules \
        --exclude="*.log" --exclude="*.json" \
        "password\|secret\|api[_-]\?key" "$PROJECT_ROOT" >/dev/null 2>&1; then
        warn "Potential secrets found in files (manual review recommended)"
    fi
    
    # Check file permissions on scripts
    find "$PROJECT_ROOT" -name "*.sh" -type f ! -perm -u+x 2>/dev/null | while read -r script; do
        warn "Script not executable: $script"
    done
    
    if [ ${#security_issues[@]} -eq 0 ]; then
        success "Basic security checks passed"
        return 0
    else
        warn "Security issues found: ${security_issues[*]}"
        return 0  # Warning, not failure
    fi
}

integration_test_basic() {
    info "🔗 Running basic integration tests..."
    
    if ! check_dependency "kubectl"; then
        warn "kubectl not available, skipping integration tests"
        return 0
    fi
    
    # Test if we can connect to any cluster
    if kubectl cluster-info >/dev/null 2>&1; then
        info "  ✅ Kubernetes cluster is accessible"
        
        # Test namespace operations
        if kubectl get namespaces >/dev/null 2>&1; then
            info "  ✅ Can list namespaces"
        else
            warn "  ⚠️  Cannot list namespaces"
        fi
    else
        warn "  ⚠️  No Kubernetes cluster accessible"
    fi
    
    success "Integration tests completed"
    return 0
}

cleanup() {
    info "🧹 Cleaning up..."
    
    # Clean up any temporary files
    rm -f /tmp/noah_test_*
    
    # Clean up test namespace if it exists
    if check_dependency "kubectl" && kubectl get namespace "$TEST_NAMESPACE" >/dev/null 2>&1; then
        info "Cleaning up test namespace: $TEST_NAMESPACE"
        kubectl delete namespace "$TEST_NAMESPACE" --ignore-not-found=true >/dev/null 2>&1 || true
    fi
    
    success "Cleanup completed"
}

show_help() {
    cat << EOF
N.O.A.H Unified Test Script

Usage: $0 [OPTIONS]

Options:
    --deps-only      Check dependencies only
    --python-only    Run Python tests only
    --helm-only      Run Helm tests only
    --yaml-only      Run YAML tests only
    --security-only  Run security tests only
    --integration    Run integration tests
    --no-cleanup     Skip cleanup
    -h, --help       Show this help

Examples:
    $0                    # Run all tests
    $0 --python-only      # Run only Python tests
    $0 --helm-only        # Run only Helm tests
    $0 --deps-only        # Check dependencies only
EOF
}

# Main execution
main() {
    local run_all=true
    local run_deps=false
    local run_python=false
    local run_helm=false
    local run_yaml=false
    local run_security=false
    local run_integration=false
    local run_cleanup=true
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --deps-only)
                run_all=false
                run_deps=true
                shift
                ;;
            --python-only)
                run_all=false
                run_python=true
                shift
                ;;
            --helm-only)
                run_all=false
                run_helm=true
                shift
                ;;
            --yaml-only)
                run_all=false
                run_yaml=true
                shift
                ;;
            --security-only)
                run_all=false
                run_security=true
                shift
                ;;
            --integration)
                run_all=false
                run_integration=true
                shift
                ;;
            --no-cleanup)
                run_cleanup=false
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Start tests
    info "🧪 Starting N.O.A.H Unified Test Suite"
    info "📅 $(date)"
    info "📂 Project root: $PROJECT_ROOT"
    info "📝 Log file: $LOG_FILE"
    echo
    
    local overall_success=true
    
    # Run tests based on options
    if [ "$run_all" = true ] || [ "$run_deps" = true ]; then
        test_dependencies || overall_success=false
        echo
    fi
    
    if [ "$run_all" = true ] || [ "$run_python" = true ]; then
        test_python_suite || overall_success=false
        echo
    fi
    
    if [ "$run_all" = true ] || [ "$run_helm" = true ]; then
        test_helm_charts_basic || overall_success=false
        echo
    fi
    
    if [ "$run_all" = true ] || [ "$run_yaml" = true ]; then
        test_yaml_syntax || overall_success=false
        echo
    fi
    
    if [ "$run_all" = true ] || [ "$run_security" = true ]; then
        test_security_basic || overall_success=false
        echo
    fi
    
    if [ "$run_integration" = true ]; then
        integration_test_basic || overall_success=false
        echo
    fi
    
    # Cleanup
    if [ "$run_cleanup" = true ]; then
        cleanup
        echo
    fi
    
    # Final results
    echo "=" * 60
    if [ "$overall_success" = true ]; then
        success "🎉 All tests passed!"
        info "📄 Full log: $LOG_FILE"
        exit 0
    else
        error "💥 Some tests failed!"
        error "📄 Check log for details: $LOG_FILE"
        exit 1
    fi
}

# Trap cleanup on exit
trap cleanup EXIT

# Run main function with all arguments
main "$@"
