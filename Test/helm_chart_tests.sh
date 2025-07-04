#!/bin/bash

# N.O.A.H - Helm Chart Unit Tests
# 
# This script performs unit testing of all Helm charts in the N.O.A.H project
# including template validation, value testing, and security checks.

set -e

# Configuration
CHARTS_DIR="../Helm"
TEST_NAMESPACE="noah-test"
LOG_FILE="/tmp/noah_helm_tests_$(date +%Y%m%d_%H%M%S).log"

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

warn() {
    log "WARN" "${YELLOW}$*${NC}"
}

error() {
    log "ERROR" "${RED}$*${NC}"
}

success() {
    log "SUCCESS" "${GREEN}$*${NC}"
}

# Check prerequisites
check_prerequisites() {
    info "Checking prerequisites for Helm chart testing..."
    
    if ! command -v helm &> /dev/null; then
        error "Helm is not installed"
        exit 1
    fi
    
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is not installed"
        exit 1
    fi
    
    # Check if helm unittest plugin is available
    if ! helm plugin list | grep -q unittest; then
        warn "Helm unittest plugin not found, installing..."
        helm plugin install https://github.com/quintush/helm-unittest
    fi
    
    success "Prerequisites check passed"
}

# Validate chart structure
validate_chart_structure() {
    local chart_path="$1"
    local chart_name=$(basename "$chart_path")
    
    info "Validating chart structure: $chart_name"
    
    # Required files
    local required_files=("Chart.yaml" "values.yaml" "templates")
    
    for file in "${required_files[@]}"; do
        if [ ! -e "$chart_path/$file" ]; then
            error "Missing required file/directory: $file in chart $chart_name"
            return 1
        fi
    done
    
    # Check Chart.yaml format
    if ! helm show chart "$chart_path" >/dev/null 2>&1; then
        error "Invalid Chart.yaml in $chart_name"
        return 1
    fi
    
    # Check values.yaml format
    if ! helm show values "$chart_path" >/dev/null 2>&1; then
        error "Invalid values.yaml in $chart_name"
        return 1
    fi
    
    success "Chart structure valid: $chart_name"
    return 0
}

# Lint Helm charts
lint_charts() {
    local chart_path="$1"
    local chart_name=$(basename "$chart_path")
    
    info "Linting chart: $chart_name"
    
    if helm lint "$chart_path"; then
        success "Chart lint passed: $chart_name"
        return 0
    else
        error "Chart lint failed: $chart_name"
        return 1
    fi
}

# Template validation
validate_templates() {
    local chart_path="$1"
    local chart_name=$(basename "$chart_path")
    
    info "Validating templates: $chart_name"
    
    # Dry run template rendering
    if helm template "$chart_name" "$chart_path" --dry-run >/dev/null 2>&1; then
        success "Template validation passed: $chart_name"
    else
        error "Template validation failed: $chart_name"
        # Show detailed error
        helm template "$chart_name" "$chart_path" --dry-run 2>&1 | tail -10
        return 1
    fi
    
    # Test with different value combinations
    local test_values=(
        "--set replicaCount=3"
        "--set ingress.enabled=true"
        "--set persistence.enabled=false"
        "--set autoscaling.enabled=true"
        "--set networkPolicy.enabled=true"
    )
    
    for values in "${test_values[@]}"; do
        if helm template "$chart_name" "$chart_path" $values --dry-run >/dev/null 2>&1; then
            success "Template test passed with: $values"
        else
            warn "Template test failed with: $values"
        fi
    done
    
    return 0
}

# Security validation
validate_security() {
    local chart_path="$1"
    local chart_name=$(basename "$chart_path")
    
    info "Running security validation: $chart_name"
    
    # Generate templates for security analysis
    local temp_dir=$(mktemp -d)
    helm template "$chart_name" "$chart_path" --output-dir "$temp_dir" 2>/dev/null
    
    local security_issues=0
    
    # Check for privileged containers
    if find "$temp_dir" -name "*.yaml" -exec grep -l "privileged: true" {} \; 2>/dev/null | head -1; then
        warn "Privileged containers found in $chart_name"
        ((security_issues++))
    fi
    
    # Check for host network usage
    if find "$temp_dir" -name "*.yaml" -exec grep -l "hostNetwork: true" {} \; 2>/dev/null | head -1; then
        warn "Host network usage found in $chart_name"
        ((security_issues++))
    fi
    
    # Check for host PID usage
    if find "$temp_dir" -name "*.yaml" -exec grep -l "hostPID: true" {} \; 2>/dev/null | head -1; then
        warn "Host PID usage found in $chart_name"
        ((security_issues++))
    fi
    
    # Check for runAsRoot
    if find "$temp_dir" -name "*.yaml" -exec grep -l "runAsUser: 0" {} \; 2>/dev/null | head -1; then
        warn "Containers running as root found in $chart_name"
        ((security_issues++))
    fi
    
    # Check for missing security contexts
    local deployment_files=$(find "$temp_dir" -name "*.yaml" -exec grep -l "kind: Deployment" {} \; 2>/dev/null)
    for deployment in $deployment_files; do
        if ! grep -q "securityContext:" "$deployment"; then
            warn "Missing security context in deployment: $deployment"
            ((security_issues++))
        fi
    done
    
    rm -rf "$temp_dir"
    
    if [ $security_issues -eq 0 ]; then
        success "Security validation passed: $chart_name"
        return 0
    else
        warn "Security validation found $security_issues issues in $chart_name"
        return 1
    fi
}

# Values validation
validate_values() {
    local chart_path="$1"
    local chart_name=$(basename "$chart_path")
    
    info "Validating values: $chart_name"
    
    # Test with minimal values
    local minimal_values=$(mktemp)
    cat > "$minimal_values" <<EOF
replicaCount: 1
image:
  repository: nginx
  tag: "latest"
  pullPolicy: IfNotPresent
EOF
    
    if helm template "$chart_name" "$chart_path" -f "$minimal_values" --dry-run >/dev/null 2>&1; then
        success "Minimal values test passed: $chart_name"
    else
        warn "Minimal values test failed: $chart_name"
    fi
    
    # Test with production-like values
    local prod_values=$(mktemp)
    cat > "$prod_values" <<EOF
replicaCount: 3
image:
  repository: nginx
  tag: "stable"
  pullPolicy: IfNotPresent
ingress:
  enabled: true
  className: nginx
  hosts:
    - host: test.local
      paths:
        - path: /
          pathType: Prefix
persistence:
  enabled: true
  size: 10Gi
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
networkPolicy:
  enabled: true
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi
EOF
    
    if helm template "$chart_name" "$chart_path" -f "$prod_values" --dry-run >/dev/null 2>&1; then
        success "Production values test passed: $chart_name"
    else
        warn "Production values test failed: $chart_name"
    fi
    
    rm -f "$minimal_values" "$prod_values"
    return 0
}

# Dependency validation
validate_dependencies() {
    local chart_path="$1"
    local chart_name=$(basename "$chart_path")
    
    info "Validating dependencies: $chart_name"
    
    if [ -f "$chart_path/Chart.yaml" ]; then
        # Check if chart has dependencies
        if grep -q "dependencies:" "$chart_path/Chart.yaml"; then
            info "Chart $chart_name has dependencies, updating..."
            
            if helm dependency update "$chart_path"; then
                success "Dependencies updated successfully: $chart_name"
            else
                error "Failed to update dependencies: $chart_name"
                return 1
            fi
        else
            info "No dependencies found for: $chart_name"
        fi
    fi
    
    return 0
}

# Integration test with dry-run install
integration_test() {
    local chart_path="$1"
    local chart_name=$(basename "$chart_path")
    
    info "Running integration test: $chart_name"
    
    # Create test namespace if it doesn't exist
    kubectl create namespace "$TEST_NAMESPACE" --dry-run=client -o yaml | kubectl apply -f - 2>/dev/null || true
    
    # Test dry-run installation
    if helm install "$chart_name-test" "$chart_path" \
        --namespace "$TEST_NAMESPACE" \
        --dry-run --debug >/dev/null 2>&1; then
        success "Integration test passed: $chart_name"
        return 0
    else
        error "Integration test failed: $chart_name"
        return 1
    fi
}

# Run unit tests (if available)
run_unit_tests() {
    local chart_path="$1"
    local chart_name=$(basename "$chart_path")
    
    if [ -d "$chart_path/tests" ]; then
        info "Running unit tests: $chart_name"
        
        if helm unittest "$chart_path"; then
            success "Unit tests passed: $chart_name"
            return 0
        else
            error "Unit tests failed: $chart_name"
            return 1
        fi
    else
        info "No unit tests found for: $chart_name"
        return 0
    fi
}

# Test individual chart
test_chart() {
    local chart_path="$1"
    local chart_name=$(basename "$chart_path")
    
    info "=== Testing Chart: $chart_name ==="
    
    local failed_tests=0
    
    validate_chart_structure "$chart_path" || ((failed_tests++))
    lint_charts "$chart_path" || ((failed_tests++))
    validate_dependencies "$chart_path" || ((failed_tests++))
    validate_templates "$chart_path" || ((failed_tests++))
    validate_values "$chart_path" || ((failed_tests++))
    validate_security "$chart_path" || ((failed_tests++))
    integration_test "$chart_path" || ((failed_tests++))
    run_unit_tests "$chart_path" || ((failed_tests++))
    
    if [ $failed_tests -eq 0 ]; then
        success "All tests passed for chart: $chart_name"
        return 0
    else
        error "$failed_tests test(s) failed for chart: $chart_name"
        return 1
    fi
}

# Main function
main() {
    info "Starting N.O.A.H Helm Chart Tests"
    info "Charts directory: $CHARTS_DIR"
    info "Test namespace: $TEST_NAMESPACE"
    info "Log file: $LOG_FILE"
    
    check_prerequisites
    
    local total_charts=0
    local failed_charts=0
    
    # Find all charts
    for chart_path in "$CHARTS_DIR"/*; do
        if [ -d "$chart_path" ] && [ -f "$chart_path/Chart.yaml" ]; then
            ((total_charts++))
            
            if ! test_chart "$chart_path"; then
                ((failed_charts++))
            fi
        fi
    done
    
    # Summary
    info "=== Test Summary ==="
    info "Total charts tested: $total_charts"
    info "Failed charts: $failed_charts"
    info "Success rate: $(( (total_charts - failed_charts) * 100 / total_charts ))%"
    
    if [ $failed_charts -eq 0 ]; then
        success "All Helm chart tests passed!"
    else
        error "$failed_charts chart(s) failed testing"
        exit 1
    fi
    
    # Cleanup test namespace
    kubectl delete namespace "$TEST_NAMESPACE" --ignore-not-found=true 2>/dev/null || true
    
    info "Test results logged to: $LOG_FILE"
}

# Run main function
main "$@"
